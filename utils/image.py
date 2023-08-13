from PIL import Image
import io
import logging
import base64
import requests
from odoo.tools import config

FIELDS_RECURSION_LIMIT = 3
ERROR_PREVIEW_BYTES = 200
DEFAULT_IMAGE_TIMEOUT = 3
DEFAULT_IMAGE_MAXBYTES = 10 * 1024 * 1024
DEFAULT_IMAGE_REGEX = r"^(?:http|https)://"
DEFAULT_IMAGE_CHUNK_SIZE = 32768

_logger = logging.getLogger(__name__)

def _import_image_by_url(self, url):
        """ Imports an image by URL
        """
        maxsize = int(config.get("import_image_maxbytes", DEFAULT_IMAGE_MAXBYTES))
        _logger.debug("Trying to import image from URL: %s" % (url))
        try:
            response = requests.get(url, timeout=int(config.get("import_image_timeout", DEFAULT_IMAGE_TIMEOUT)))
            response.raise_for_status()

            if response.headers.get('Content-Length') and int(response.headers['Content-Length']) > maxsize:
                raise ValueError(("File size exceeds configured maximum (%s bytes)", maxsize))

            content = bytearray()
            for chunk in response.iter_content(DEFAULT_IMAGE_CHUNK_SIZE):
                content += chunk
                if len(content) > maxsize:
                    raise ValueError(("File size exceeds configured maximum (%s bytes)", maxsize))

            image = Image.open(io.BytesIO(content))
            w, h = image.size
            if w * h > 42e6:  # Nokia Lumia 1020 photo resolution
                raise ValueError(
                    u"Image size excessive, imported images must be smaller "
                    u"than 42 million pixel")

            return base64.b64encode(content)
        except Exception as e:
            _logger.exception(e)
            raise ValueError(("Could not retrieve URL: %(url)s %(error)s") % {
                'url': url,
                'error': e
            })