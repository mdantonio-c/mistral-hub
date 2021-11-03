import io
import sys

import dballe

# body = sys.stdin.encode()

# bodyfile = io.BytesIO(body)
importer = dballe.Importer("JSON", domain_errors="tag")
exporter = dballe.Exporter("BUFR")

# with importer.from_file(bodyfile) as f:
with importer.from_file(sys.stdin.buffer) as f:

    for msg in f:
        bodybufr = exporter.to_binary(msg)
        sys.stdout.buffer.write(bodybufr)
