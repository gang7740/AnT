##Find Missed Files

import os

def find_missing_files(folder_path, n):
    all_files = set()
    
    # 폴더와 하위 폴더를 모두 검색합니다.
    for root, _, files in os.walk(folder_path):
        for file in files:
            # 파일 이름에서 숫자만 가져와서 저장합니다.
            try:
                file_number = int(file.split('.')[0])  # 확장자가 있다면 . 이전까지만 숫자 취급
                all_files.add(file_number)
            except ValueError:
                pass  # 숫자가 아닌 파일 이름은 무시

    # 1부터 n까지 범위에서 없는 번호를 찾습니다.
    missing_files = [num for num in range(1, n + 1) if num not in all_files]
    
    return missing_files

# 사용 예시
folder_path = 'D:\work\dataset\info_test_dataset'  # 대상 폴더 경로 입력
n = 426  # 파일 번호 범위 (1부터 n까지)
missing_files = find_missing_files(folder_path, n)

print("빠진 파일 번호:", missing_files)
