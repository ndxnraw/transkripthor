# Production Qt Quick frontend; both ASR backends and existing project formats.
from pathlib import Path
QML_APP = True
exec(compile((Path(SPECPATH) / 'TranskripTHOR.spec').read_text(encoding='utf-8'), 'TranskripTHOR.spec', 'exec'))
