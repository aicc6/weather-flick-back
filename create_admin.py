#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
"""

import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.auth import get_password_hash, check_password_strength

def create_admin_user():
    """관리자 계정 생성"""
    print("=== 관리자 계정 생성 ===\n")

    # 데이터베이스 연결
    db = next(get_db())

    try:
        # 사용자 입력 받기
        email = input("관리자 이메일을 입력하세요: ").strip()
        username = input("관리자 사용자명을 입력하세요: ").strip()
        password = input("관리자 비밀번호를 입력하세요: ").strip()

        # 입력 검증
        if not email or not username or not password:
            print("❌ 모든 필드를 입력해주세요.")
            return

        # 이메일 중복 확인
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ 이메일 '{email}'은 이미 등록되어 있습니다.")
            return

        # 사용자명 중복 확인
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"❌ 사용자명 '{username}'은 이미 사용 중입니다.")
            return

        # 비밀번호 강도 검사
        password_check = check_password_strength(password)
        if not password_check["is_valid"]:
            print("❌ 비밀번호가 너무 약합니다:")
            for error in password_check["errors"]:
                print(f"   - {error}")
            return

        # 관리자 계정 생성
        hashed_password = get_password_hash(password)
        admin_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print(f"\n✅ 관리자 계정이 성공적으로 생성되었습니다!")
        print(f"   이메일: {admin_user.email}")
        print(f"   사용자명: {admin_user.username}")
        print(f"   역할: {admin_user.role.value}")
        print(f"   계정 ID: {admin_user.id}")
        print(f"\n이제 이 계정으로 로그인하여 관리자 기능을 사용할 수 있습니다.")

    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
        db.rollback()
    finally:
        db.close()

def list_admin_users():
    """관리자 계정 목록 조회"""
    print("=== 관리자 계정 목록 ===\n")

    db = next(get_db())

    try:
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()

        if not admin_users:
            print("관리자 계정이 없습니다.")
            return

        print(f"총 {len(admin_users)}개의 관리자 계정이 있습니다:\n")

        for i, user in enumerate(admin_users, 1):
            print(f"{i}. ID: {user.id}")
            print(f"   이메일: {user.email}")
            print(f"   사용자명: {user.username}")
            print(f"   활성화: {'예' if user.is_active else '아니오'}")
            print(f"   인증: {'예' if user.is_verified else '아니오'}")
            print(f"   생성일: {user.created_at}")
            print(f"   마지막 로그인: {user.last_login or '없음'}")
            print()

    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
    finally:
        db.close()

def main():
    """메인 함수"""
    print("Weather Flick 관리자 계정 관리 도구\n")

    while True:
        print("1. 관리자 계정 생성")
        print("2. 관리자 계정 목록 조회")
        print("3. 종료")

        choice = input("\n선택하세요 (1-3): ").strip()

        if choice == "1":
            create_admin_user()
        elif choice == "2":
            list_admin_users()
        elif choice == "3":
            print("프로그램을 종료합니다.")
            break
        else:
            print("❌ 잘못된 선택입니다. 1-3 중에서 선택해주세요.")

        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
