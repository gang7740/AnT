import os
import random
from PIL import Image

# 설정
folder_path = 'D:\\work\\dataset\\info_test_dataset'
subfolder_names = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
categories = ['1', '2', '3']  # '1', '2', '3' 폴더 각각으로 이미지를 생성
num_images = 20  # 전체에서 가져올 이미지 수
thumbnail_size = (1024, 1024)  # 각 썸네일의 크기
output_width = 5120  # 합쳐진 이미지의 가로 길이
output_image_paths = {
    '1': 'combined_image_category_1.jpg',
    '2': 'combined_image_category_2.jpg',
    '3': 'combined_image_category_3.jpg'
}  # 각 결과 이미지 파일명

# 이미지 합성 함수
def create_combined_image(category, images):
    rows, cols = 2, 5
    thumbnail_width, thumbnail_height = thumbnail_size
    output_height = rows * thumbnail_height
    combined_image = Image.new('RGB', (output_width, output_height))

    # 이미지 배치
    for idx, img in enumerate(images[:20]):  # 4 x 5 이미지만 사용
        row = idx // cols
        col = idx % cols
        x = col * thumbnail_width
        y = row * thumbnail_height
        combined_image.paste(img, (x, y))

    # 저장
    combined_image.save(output_image_paths[category])
    print(f"{category} 폴더 이미지가 {output_image_paths[category]}에 저장되었습니다.")

# 각 카테고리에 대해 이미지 가져오기 및 합성
for category in categories:
    images = []
    for subfolder in subfolder_names:
        category_path = os.path.join(folder_path, subfolder, category)
        if not os.path.isdir(category_path):
            print(f"폴더 {category_path}을(를) 찾을 수 없습니다.")
            continue
        # 카테고리 폴더에서 이미지 파일 리스트 생성
        image_files = [f for f in os.listdir(category_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        images.extend([os.path.join(category_path, f) for f in image_files])  # 전체 파일 경로를 저장

    # 이미지가 20개 이상인 경우에만 처리
    if len(images) >= num_images:
        selected_images = random.sample(images, num_images)  # 전체에서 20개 랜덤 선택
        loaded_images = [Image.open(img_path).resize(thumbnail_size) for img_path in selected_images]
        create_combined_image(category, loaded_images)
    else:
        print(f"{category} 폴더에서 충분한 이미지를 찾을 수 없습니다.")
