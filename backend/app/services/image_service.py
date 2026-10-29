from PIL import Image, ImageDraw


def write_annotated_image(image_path, detections, output_path):
    """Create a separate derivative; never modify the original image."""
    with Image.open(image_path) as source:
        image = source.convert('RGB')
    draw = ImageDraw.Draw(image)
    for detection in detections:
        box = detection['bbox']
        coordinates = (box['x1'], box['y1'], box['x2'], box['y2'])
        draw.rectangle(coordinates, outline=(0, 220, 255), width=3)
        draw.text((box['x1'], max(0, box['y1'] - 18)), detection['label'], fill=(0, 220, 255))
    image.save(output_path, format='JPEG', quality=92)
