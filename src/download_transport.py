"""Supervised local Hub worker: bounded waiting, resumable cache, no raw errors."""
from i18n import tr
import logging
import multiprocessing
import os
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app_errors import CategorizedError


@dataclass(frozen=True)
class DownloadLimits:
    idle: float = 90
    verification_idle: float = 180
    phase_max: float = 21600
    attempts: int = 3
    backoff: float = 2


def diagnostic_logger(cache):
    logger = logging.Logger('model_download')
    if not logger.handlers:
        Path(cache).mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(Path(cache)/'model-download.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def status_text(event, silent=0):
    labels = {'connect':tr('download_transport.status_text.connecting'), 'lock':tr('download_transport.status_text.waiting_for_the_cache_lock'), 'transfer':tr('download_transport.status_text.downloading'),
              'verify':tr('download_transport.labels.verifying_contents'), 'finalize':tr('download_transport.status_text.finalizing_file'), 'ready':tr('download_transport.status_text.model_is_ready')}
    text = labels.get(event['phase'], tr('download_transport.labels.preparing_model')) + ': ' + event.get('file','model')
    current, total = event.get('bytes',0), event.get('total')
    if total:
        text += f' • {current/1024**2:.1f}/{total/1024**2:.1f} MB'
    if event.get('count'):
        text += tr('download_transport.status_text.file', p0=event['count'])
    if silent >= 5:
        text += tr('download_transport.status_text.no_progress_for_s_timeout_is_active', p0=int(silent))
    return text


def supervise(cache, model, emit, stop, limits=DownloadLimits(), worker=None, revision=None, verify_only=False):
    from download_worker import run_download
    context = multiprocessing.get_context('spawn')
    logger = diagnostic_logger(cache)
    logger.info('start model=%s transport=HTTP hub=0.36.2 xet=disabled', model)
    emit('download_state', True)
    try:
        for attempt in range(limits.attempts):
            if stop.is_set():
                raise InterruptedError(tr('download_transport.supervise.download_stopped_partial_files_remain_cached_select_download_again'))
            receiver, sender = context.Pipe(duplex=False)
            args = (str(cache), model, sender) if revision is None else (str(cache), model, sender, revision)
            if verify_only:
                args = (str(cache), model, sender, revision, True)
            process = context.Process(target=worker or run_download, args=args, daemon=True)
            event = dict(phase='connect',file=model)
            started = changed = last_ui = time.monotonic()
            signature = None
            failure = None
            category = 'network'
            complete = False
            try:
                process.start()
                sender.close()
                while True:
                    if stop.is_set():
                        raise InterruptedError(tr('download_transport.supervise.download_stopped_partial_files_remain_cached_select_download_again'))
                    try:
                        if receiver.poll(.1):
                            message = receiver.recv()
                            if message['kind'] == 'complete':
                                complete = True
                                break
                            if message['kind'] == 'error':
                                failure = (message['message'],message['retry'])
                                code = message['code']
                                category = ('disk' if code == 'os_28' else 'permission' if code in ('os_13', 'os_1')
                                            else 'model' if code in ('integrity', 'metadata') or code.startswith('http_4') and code not in ('http_408', 'http_429')
                                            else 'memory' if code == 'internal_MemoryError'
                                            else 'network' if code in ('connection', 'timeout', 'tls', 'incomplete') or code.startswith('http_')
                                            else 'unknown')
                                logger.warning('failure attempt=%s code=%s',attempt+1,message['code'])
                                break
                            event = message
                            new_signature = (event['phase'],event.get('file'),event.get('bytes'))
                            now = time.monotonic()
                            if new_signature != signature:
                                if signature is None or new_signature[:2] != signature[:2]:
                                    started = now
                                    logger.info('phase=%s file=%s attempt=%s',event['phase'],event.get('file'),attempt+1)
                                signature, changed = new_signature, now
                    except EOFError:
                        failure = (tr('download_transport.supervise.the_download_process_ended_unexpectedly_try_again_check_available'),True)
                        break
                    now = time.monotonic()
                    timeout = limits.verification_idle if event['phase'] in ('verify','finalize') else limits.idle
                    if now-changed > timeout or now-started > limits.phase_max:
                        failure = (tr('download_transport.supervise.timeout_check_your_connection_free_disk_space_or_another', p0=status_text(event)),True)
                        logger.warning('timeout phase=%s file=%s idle_seconds=%.1f',event['phase'],event.get('file'),now-changed)
                        break
                    if now-last_ui >= .5:
                        emit('status',status_text(event,now-changed))
                        last_ui = now
                    if not process.is_alive() and not receiver.poll():
                        failure = (tr('download_transport.supervise.the_download_process_ended_unexpectedly_try_again'),True)
                        break
            finally:
                if process.pid:
                    process.join(.5 if complete else 0)
                    if process.is_alive():
                        process.terminate()
                        process.join(2)
                    if process.is_alive():
                        process.kill()
                        process.join(2)
                    process.close()
                sender.close()
                receiver.close()
            if complete:
                logger.info('complete model=%s',model)
                emit('status',tr('download_transport.supervise.model_verified_and_available_locally'))
                return
            message, retry = failure
            if not retry or attempt+1 == limits.attempts:
                raise CategorizedError(category, message)
            delay = limits.backoff * 2**attempt
            emit('status',tr('download_transport.supervise.retry_in_s_completed_files_will_be_kept', p0=message, p1=attempt + 2, p2=limits.attempts, p3=delay))
            if stop.wait(delay):
                raise InterruptedError(tr('download_transport.supervise.download_stopped_cached_data_will_be_kept'))
    finally:
        logger.info('download session ended')
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        emit('download_state', False)
