from pathlib import Path
BASIC_DISTRIBUTION = True
exec(compile((Path(SPECPATH) / 'TranskripTHOR.spec').read_text(encoding='utf-8'),
             str(Path(SPECPATH) / 'TranskripTHOR.spec'), 'exec'))
