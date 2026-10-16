import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from helpers.tests_factories import AdminAPITestCase

PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-image-body"


class FileAPITests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        settings_override = override_settings(MEDIA_ROOT=self.media_root)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.images_dir = os.path.join(self.media_root, "images")

    def upload(self, url, field, files):
        return self.client.post(url, {field: files}, format="multipart")

    def stored_files(self):
        return sorted(os.listdir(self.images_dir)) if os.path.isdir(self.images_dir) else []

    def test_upload_single_image(self):
        response = self.upload("/files/image/", "image", SimpleUploadedFile("Photo.PNG", PNG_BYTES))
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body["filename"].endswith(".png"))
        self.assertEqual(body["path"], f"/media/images/{body['filename']}")
        self.assertEqual(self.stored_files(), [body["filename"]])
        with open(os.path.join(self.images_dir, body["filename"]), "rb") as stored:
            self.assertEqual(stored.read(), PNG_BYTES)

    def test_single_upload_validation(self):
        response = self.client.post("/files/image/", {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Image field is required")
        response = self.upload("/files/image/", "image", SimpleUploadedFile("notes.txt", b"hi"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Unsupported image extension: .txt")
        self.assertEqual(self.stored_files(), [])

    def test_upload_multiple_images(self):
        files = [SimpleUploadedFile(name, PNG_BYTES) for name in ("a.jpg", "b.webp", "C.PNG")]
        response = self.upload("/files/images/", "images", files)
        self.assertEqual(response.status_code, 201, response.content)
        names = [item["filename"] for item in response.json()]
        self.assertEqual([os.path.splitext(n)[1] for n in names], [".jpg", ".webp", ".png"])
        self.assertEqual([item["path"] for item in response.json()],
                         [f"/media/images/{n}" for n in names])
        self.assertEqual(self.stored_files(), sorted(names))

    def test_multiple_upload_rejects_whole_batch_on_bad_extension(self):
        files = [SimpleUploadedFile("ok.png", PNG_BYTES), SimpleUploadedFile("bad.exe", b"MZ")]
        response = self.upload("/files/images/", "images", files)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid image extension: .exe")
        self.assertEqual(self.stored_files(), [])
        empty = self.client.post("/files/images/", {}, format="multipart")
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json()["message"], "Images field is required")

    def test_delete_image(self):
        uploaded = self.upload("/files/image/", "image", SimpleUploadedFile("x.gif", PNG_BYTES))
        filename = uploaded.json()["filename"]
        response = self.client.delete(f"/files/image/{filename}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.stored_files(), [])
        missing = self.client.delete(f"/files/image/{filename}/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["message"], "File not found")

    def test_delete_rejects_parent_directory_names(self):
        response = self.client.delete("/files/image/..secret/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid filename")

    def test_endpoints_require_authentication(self):
        self.client.force_authenticate(None)
        responses = [
            self.upload("/files/image/", "image", SimpleUploadedFile("a.png", PNG_BYTES)),
            self.upload("/files/images/", "images", [SimpleUploadedFile("a.png", PNG_BYTES)]),
            self.client.delete("/files/image/a.png/"),
        ]
        for response in responses:
            self.assertIn(response.status_code, (401, 403))
        self.assertEqual(self.stored_files(), [])
