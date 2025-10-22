"""Avatar service for handling image uploads and processing."""

from __future__ import annotations

import base64
import io

from fastapi import UploadFile
from PIL import Image

from app.schemas.avatar import CropData
from common.core.logging_service import get_logger
from shared_db.models.user import AvatarType

logger = get_logger(__name__)

# Avatar configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZE = 150  # 150x150px
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


class AvatarService:
    """Service for handling avatar uploads and processing."""

    def __init__(self) -> None:
        """Initialize avatar service."""

    async def process_uploaded_avatar(
        self,
        file: UploadFile,
        crop_data: CropData | None = None,
        background_color: tuple[int, int, int] = (255, 255, 255),
    ) -> tuple[str, AvatarType]:
        """Process an uploaded avatar image file.

        Args:
            file: The uploaded file
            crop_data: Optional crop data for custom cropping
            background_color: RGB tuple for transparent image background (default: white)

        Returns:
            Tuple of (base64_encoded_image, avatar_type)

        Raises:
            ValueError: If file is invalid or processing fails
        """
        if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid file type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}")

        if file.size and file.size > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB")

        try:
            # Read file content
            content = await file.read()

            # Validate image
            image = Image.open(io.BytesIO(content))
            image.verify()  # Verify it's a valid image

            # Reopen after verify (which closes the file)
            image = Image.open(io.BytesIO(content))

            # Convert to RGB if necessary (for PNG transparency)
            if image.mode in ("RGBA", "LA", "P"):
                # Create a background with the specified color for transparent images
                background = Image.new("RGB", image.size, background_color)
                if image.mode == "P":
                    image = image.convert("RGBA")
                if image.mode == "RGBA":
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = background
                else:
                    image = image.convert("RGB")

            # Apply crop if provided
            if crop_data:
                image = self._apply_crop(image, crop_data)
            else:
                # Default: resize and crop to square (center crop)
                image = self._resize_and_crop_to_square(image, AVATAR_SIZE)

            # Convert to WebP for better compression
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="WebP", quality=85, optimize=True)

            # Encode to base64
            image_base64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")
            data_url = f"data:image/webp;base64,{image_base64}"

            logger.info(f"Successfully processed avatar for {file.filename or 'unknown file'}")
            return data_url, AvatarType.UPLOADED

        except Exception as e:
            logger.exception(f"Failed to process avatar: {e!s}")
            raise ValueError(f"Failed to process image: {e!s}")

    async def process_url_avatar(self, image_url: str) -> tuple[str, AvatarType]:
        """Process an avatar from a URL (for Gmail profile pictures).

        Args:
            image_url: URL of the image

        Returns:
            Tuple of (base64_encoded_image, avatar_type)

        Raises:
            ValueError: if URL processing fails
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                _ = response.raise_for_status()

                # Process the downloaded image
                image = Image.open(io.BytesIO(response.content))
                image.verify()

                # Reopen after verify
                image = Image.open(io.BytesIO(response.content))

                # Convert to RGB if necessary
                if image.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    if image.mode == "RGBA":
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    else:
                        image = image.convert("RGB")

                # Resize and crop to square
                image = self._resize_and_crop_to_square(image, AVATAR_SIZE)

                # Convert to WebP
                output_buffer = io.BytesIO()
                image.save(output_buffer, format="WebP", quality=85, optimize=True)

                # Encode to base64
                image_base64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")
                data_url = f"data:image/webp;base64,{image_base64}"

                logger.info(f"Successfully processed avatar from URL: {image_url}")
                return data_url, AvatarType.GOOGLE

        except Exception as e:
            logger.exception(f"Failed to process avatar from URL {image_url}: {e!s}")
            raise ValueError(f"Failed to process image from URL: {e!s}")

    def _apply_crop(self, image: Image.Image, crop_data: CropData) -> Image.Image:
        """Apply crop data to an image.

        Args:
            image: PIL Image to crop
            crop_data: Crop coordinates and size

        Returns:
            Cropped and resized PIL Image
        """
        # Extract crop coordinates
        x = int(crop_data.x)
        y = int(crop_data.y)
        size = int(crop_data.size)

        # Ensure crop area is within image bounds
        width, height = image.size
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))

        # Calculate crop box
        right = min(x + size, width)
        bottom = min(y + size, height)

        # Ensure we have a valid crop area
        if right <= x or bottom <= y:
            # Fallback to center crop if invalid
            return self._resize_and_crop_to_square(image, AVATAR_SIZE)

        # Crop the image
        cropped = image.crop((x, y, right, bottom))

        # Resize to avatar size
        cropped = cropped.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)  # type: ignore

        return cropped

    def _resize_and_crop_to_square(self, image: Image.Image, size: int) -> Image.Image:
        """Resize an image to a square by cropping and resizing.

        Args:
            image: PIL Image to process
            size: Target size for the square (both width and height)

        Returns:
            Processed PIL Image
        """
        # Get current dimensions
        width, height = image.size

        # Calculate crop dimensions for center crop
        if width > height:
            # Landscape: crop width
            left = (width - height) // 2
            top = 0
            right = left + height
            bottom = height
        else:
            # Portrait or square: crop height
            left = 0
            top = (height - width) // 2
            right = width
            bottom = top + width

        # Crop to square
        image = image.crop((left, top, right, bottom))

        # Resize to target size
        image = image.resize((size, size), Image.Resampling.LANCZOS)  # type: ignore

        return image

    def generate_default_avatar_url(self, username: str, background_color: str | None = None) -> str:
        """Generate a default avatar with initials.

        Args:
            username: Username to generate initials from
            background_color: Optional background color (hex)

        Returns:
            Data URL of generated avatar
        """
        # Extract initials
        initials = self._get_initials(username)

        # Generate color based on username if not provided
        if background_color is None:
            background_color = self._generate_color_from_string(username)

        try:
            # Create image with white background
            image = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), "white")

            # Convert to RGBA for transparency support
            image = image.convert("RGBA")

            # Use PIL for text rendering
            from PIL import ImageDraw, ImageFont

            draw = ImageDraw.Draw(image)

            # Draw colored circle background
            margin = 10
            draw.ellipse([margin, margin, AVATAR_SIZE - margin, AVATAR_SIZE - margin], fill=background_color)

            # Try to load a font, fallback to default if not available
            try:
                font_size = AVATAR_SIZE // 3
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except OSError:
                try:
                    # Try other common font paths
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", AVATAR_SIZE // 3)
                except OSError:
                    # Use default font
                    font = ImageFont.load_default()

            # Draw initials in white
            text_bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            text_x = (AVATAR_SIZE - text_width) // 2
            text_y = (AVATAR_SIZE - text_height) // 2

            draw.text((text_x, text_y), initials, fill="white", font=font)

            # Convert to WebP and encode
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="WebP", quality=85, optimize=True)

            image_base64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")
            data_url = f"data:image/webp;base64,{image_base64}"

            return data_url

        except Exception as e:
            logger.exception(f"Failed to generate default avatar: {e!s}")
            # Return fallback simple colored square
            return self._generate_fallback_avatar(initials, background_color)

    def _get_initials(self, username: str) -> str:
        """Extract initials from username."""
        # Remove special characters and split
        import re

        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", username).strip()

        if not cleaned:
            return "?"

        parts = cleaned.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        else:
            return cleaned[:2].upper()

    def _generate_color_from_string(self, text: str) -> str:
        """Generate a consistent color from a string."""
        import hashlib

        # Simple hash-based color generation
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()

        # Extract RGB values from hash
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)

        # Ensure colors are not too light or too dark
        r = max(100, min(200, r))
        g = max(100, min(200, g))
        b = max(100, min(200, b))

        return f"#{r:02x}{g:02x}{b:02x}"

    def _generate_fallback_avatar(self, initials: str, color: str) -> str:
        """Generate a simple fallback avatar using SVG."""
        svg_template = f"""
        <svg width="{AVATAR_SIZE}" height="{AVATAR_SIZE}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="{color}"/>
            <text x="50%" y="50%" text-anchor="middle" dy=".3em"
                  font-family="Arial, sans-serif" font-size="{AVATAR_SIZE // 3}"
                  font-weight="bold" fill="white">{initials}</text>
        </svg>
        """

        # Encode SVG to base64
        svg_base64 = base64.b64encode(svg_template.encode()).decode("utf-8")
        return f"data:image/svg+xml;base64,{svg_base64}"
