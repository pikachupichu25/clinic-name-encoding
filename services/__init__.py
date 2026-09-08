"""Thai NLP services for the clinic name encoder."""

import os
import tempfile

# PyThaiNLP creates (and later downloads into) its data directory while the
# package is being imported. Serverless hosts such as Vercel/AWS Lambda give the
# function a read-only home directory, so that import raises
# `OSError: [Errno 30] Read-only file system`. Point the data directory at the
# writable temp directory whenever home is not writable. This must run before
# any `pythainlp` import in this package.
if not os.getenv("PYTHAINLP_DATA") and not os.getenv("PYTHAINLP_DATA_DIR"):
    if not os.access(os.path.expanduser("~"), os.W_OK):
        os.environ["PYTHAINLP_DATA"] = os.path.join(
            tempfile.gettempdir(), "pythainlp-data"
        )
