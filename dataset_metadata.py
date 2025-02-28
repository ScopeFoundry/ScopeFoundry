from dataclasses import dataclass
from ScopeFoundry.cb32_uuid import cb32_uuid


import time
from datetime import datetime
from pathlib import Path


@dataclass
class DatasetMetadata:
    unique_id: str  # persistent identifier for dataset
    u: str
    t0: int
    h5_file_path: Path

    def get_file_path(self, suffix: str = ".h5") -> Path:
        return self.h5_file_path.with_suffix(suffix)


def new_dataset_metadata(measurement=None, fname: str = None) -> DatasetMetadata:
    unique_id, u = cb32_uuid()  # persistent identifier for dataset
    t0 = time.time()

    if fname is None and measurement is not None:
        app = measurement.app
        fname = app.settings["data_fname_format"].format(
            app=app,
            measurement=measurement,
            timestamp=datetime.fromtimestamp(t0),
            unique_id=unique_id,
            unique_id_short=unique_id[0:13],
            ext="h5",
        )
    elif fname is None:
        fname = f"{datetime.fromtimestamp(t0):%y%m%d_%H%M%S}.h5"
    else:
        fname = Path(fname).with_suffix(".h5")
    h5_file_path = Path(app.settings["save_dir"]) / fname
    return DatasetMetadata(unique_id, u, t0, h5_file_path)
