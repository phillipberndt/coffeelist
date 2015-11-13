from django.test import TestCase

import subprocess
import PIL.Image
import PIL.ImageDraw
import StringIO

from . import utils

# Create your tests here.
class TestDetection(TestCase):
    def test_detect(self):
        generated_pdf = utils.generate_lists(((1337, [ "0" ] * 10),)).getvalue()

        try:
            converter = subprocess.Popen(["convert", "-density", "300", "-", "-quality", "80", "jpg:"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            image_data, stderr = converter.communicate(generated_pdf)
        except:
            self.skipTest("convert utility from ImageMagick not available")
            return

        image = PIL.Image.open(StringIO.StringIO(image_data))

        # Draw a cross into the first line
        draw = PIL.ImageDraw.Draw(image)
        draw.line((760, 420, 730, 470), fill=0, width=10)
        draw.line((730, 420, 760, 470), fill=0, width=10)

        processed_image, meta_data, cross_counts, positions = utils.scan_list(image)

        self.assertEqual(cross_counts[0], 1)
        self.assertIn("1337", meta_data)
        self.assertGreater(positions[0], 200)
        for i in range(1, 10):
            self.assertGreater(positions[i], positions[i-1])
            self.assertEqual(cross_counts[i], 0)
        self.assertEqual(positions[10], 0)
