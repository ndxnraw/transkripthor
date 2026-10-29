# Same pinned services/runtime and metadata, separate UI entry and distribution.
from pathlib import Path
QML_PROTOTYPE = True
exec(compile((Path(SPECPATH) / 'TranskripTHOR.spec').read_text(encoding='utf-8'), 'TranskripTHOR.spec', 'exec'))
