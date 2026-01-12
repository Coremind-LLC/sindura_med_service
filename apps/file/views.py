import os
import uuid
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from config import settings

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tiff",
    ".tif",
    ".svg",
}


class FileViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="image")
    def upload_image(self, request):
        try:
            image = request.FILES.get("image")
            if not image:
                return Response(
                    {"message": "Image field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            original_extension = os.path.splitext(image.name)[1].lower()
            if original_extension not in ALLOWED_IMAGE_EXTENSIONS:
                return Response(
                    {"message": f"Unsupported image extension: {original_extension}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            upload_directory = os.path.join(settings.MEDIA_ROOT, "images")
            os.makedirs(upload_directory, exist_ok=True)

            filename = f"{uuid.uuid4().hex}{original_extension}"
            upload_path = os.path.join(upload_directory, filename)

            with open(upload_path, "wb+") as destination:
                for chunk in image.chunks():
                    destination.write(chunk)

            return Response(
                {
                    "filename": filename,
                    "path": f"{settings.MEDIA_URL}images/{filename}",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"message": f"Failed upload image: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="images")
    def upload_images(self, request):
        try:
            images = request.FILES.getlist("images")
            if not images:
                return Response(
                    {"message": "Images field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for image in images:
                original_extension = os.path.splitext(image.name)[1].lower()
                if original_extension not in ALLOWED_IMAGE_EXTENSIONS:
                    return Response(
                        {"message": f"Invalid image extension: {original_extension}"},
                        status=400,
                    )

            upload_directory = os.path.join(settings.MEDIA_ROOT, "images")
            os.makedirs(upload_directory, exist_ok=True)

            saved_files = []

            for image in images:
                original_extension = os.path.splitext(image.name)[1]
                filename = f"{uuid.uuid4().hex}{original_extension}"
                upload_path = os.path.join(upload_directory, filename)

                with open(upload_path, "wb+") as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)

                saved_files.append(
                    {
                        "filename": filename,
                        "path": f"{settings.MEDIA_URL}images/{filename}",
                    }
                )

            return Response(saved_files, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"message": f"Failed upload images: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["delete"],
        url_path=r"image/(?P<filename>[a-zA-Z0-9_\-\.]+)",
    )
    def delete_image(self, request, filename=None):
        if not filename:
            return Response(
                {"message": "Filename is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if ".." in filename or "/" in filename or "\\" in filename:
            return Response(
                {"message": "Invalid filename"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_path = os.path.join(settings.MEDIA_ROOT, "images", filename)

        if not os.path.exists(file_path):
            return Response(
                {"message": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            os.remove(file_path)
            return Response(
                {"message": "Image deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception as e:
            return Response(
                {"message": f"Failed to delete image: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )