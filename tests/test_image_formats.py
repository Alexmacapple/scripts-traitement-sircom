from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image, ImageCms

from sircom2026.image_formats import (
    ACCEPTED_SOURCE_IMAGE_EXTENSIONS,
    HEIC_DECISION,
    REFUSED_SOURCE_IMAGE_EXTENSIONS,
    pillow_support_report,
    prepare_image_for_jpeg,
)
from sircom2026.images import INSPECTABLE_IMAGE_EXTENSIONS


def image_bytes(
    image: Image.Image,
    image_format: str,
    **save_kwargs: object,
) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format, **save_kwargs)
    return output.getvalue()


class ImageFormatDecisionTest(unittest.TestCase):
    def test_v1_accepts_only_validated_source_extensions(self) -> None:
        self.assertEqual(
            ACCEPTED_SOURCE_IMAGE_EXTENSIONS,
            (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"),
        )
        self.assertEqual(INSPECTABLE_IMAGE_EXTENSIONS, ACCEPTED_SOURCE_IMAGE_EXTENSIONS)
        self.assertNotIn(".heic", ACCEPTED_SOURCE_IMAGE_EXTENSIONS)
        self.assertNotIn(".heif", ACCEPTED_SOURCE_IMAGE_EXTENSIONS)

    def test_pillow_support_report_documents_required_codecs_and_heic_refusal(self) -> None:
        report = pillow_support_report()

        self.assertRegex(report["pillow_version"], r"^\d+\.\d+\.\d+")
        for image_format in ("JPEG", "PNG", "WEBP", "TIFF"):
            self.assertTrue(report["accepted_formats"][image_format]["registered"])
        self.assertTrue(report["features"]["jpeg"])
        self.assertTrue(report["features"]["png_zlib"])
        self.assertTrue(report["features"]["tiff"])
        self.assertTrue(report["features"]["webp"])
        self.assertTrue(report["features"]["littlecms2"])
        for dependency in (
            "libjpeg_turbo",
            "littlecms2",
            "png_zlib",
            "tiff",
            "webp",
        ):
            version = report["feature_versions"][dependency]
            self.assertIsNotNone(version, dependency)
            self.assertRegex(version, r"\d")
        self.assertEqual(HEIC_DECISION, "refused")
        self.assertEqual(report["heic"]["decision"], "refused")
        self.assertIsNone(report["heic"]["registered_heic"])
        self.assertIsNone(report["heic"]["registered_heif"])
        self.assertIn(".heic", REFUSED_SOURCE_IMAGE_EXTENSIONS)
        self.assertIn(".heif", REFUSED_SOURCE_IMAGE_EXTENSIONS)

    def test_jpeg_png_webp_and_tiff_roundtrip_to_jpeg_ready_rgb(self) -> None:
        cases = {
            "JPEG": Image.new("RGB", (12, 8), (200, 10, 10)),
            "PNG": Image.new("RGB", (12, 8), (10, 200, 10)),
            "WEBP": Image.new("RGB", (12, 8), (10, 10, 200)),
            "TIFF": Image.new("RGB", (12, 8), (30, 40, 50)),
        }
        for image_format, source in cases.items():
            with self.subTest(format=image_format):
                payload = image_bytes(source, image_format)
                with Image.open(BytesIO(payload)) as opened:
                    prepared = prepare_image_for_jpeg(opened)
                    output = image_bytes(prepared, "JPEG", quality=100, dpi=(300, 300))
                    with Image.open(BytesIO(output)) as jpeg:
                        self.assertEqual(jpeg.format, "JPEG")
                        self.assertEqual(jpeg.mode, "RGB")
                        self.assertEqual(jpeg.size, (12, 8))
                        self.assertEqual(jpeg.info["dpi"], (300, 300))

    def test_exif_orientation_is_applied_before_jpeg_conversion(self) -> None:
        source = Image.new("RGB", (12, 8), (20, 40, 80))
        exif = Image.Exif()
        exif[274] = 6
        payload = image_bytes(source, "JPEG", exif=exif)

        with Image.open(BytesIO(payload)) as opened:
            prepared = prepare_image_for_jpeg(opened)

        self.assertEqual(prepared.mode, "RGB")
        self.assertEqual(prepared.size, (8, 12))

    def test_transparency_is_flattened_on_white_for_jpeg(self) -> None:
        source = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        source.putpixel((1, 0), (10, 20, 30, 255))
        payload = image_bytes(source, "PNG")

        with Image.open(BytesIO(payload)) as opened:
            prepared = prepare_image_for_jpeg(opened)

        self.assertEqual(prepared.mode, "RGB")
        self.assertEqual(prepared.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(prepared.getpixel((1, 0)), (10, 20, 30))

    def test_icc_profile_is_read_and_preserved_for_jpeg_output(self) -> None:
        source = Image.new("RGB", (4, 4), (80, 80, 80))
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
        icc_profile = profile.tobytes()
        payload = image_bytes(source, "JPEG", icc_profile=icc_profile)

        with Image.open(BytesIO(payload)) as opened:
            self.assertEqual(opened.info["icc_profile"], icc_profile)
            prepared = prepare_image_for_jpeg(opened)

        self.assertEqual(prepared.info["icc_profile"], icc_profile)


if __name__ == "__main__":
    unittest.main()
