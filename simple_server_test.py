#!/usr/bin/env python3
"""
간단한 서버 테스트
"""

import asyncio
import uvicorn
from fastapi import FastAPI

# 기본 앱 생성
app = FastAPI(title="Simple Test Server")

@app.get("/")
async def root():
    return {"message": "Simple test server is running!"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "Test endpoint works!"}

if __name__ == "__main__":
    print("🚀 간단한 테스트 서버를 시작합니다...")
    print("📍 http://localhost:8001 에서 접속 가능합니다.")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
