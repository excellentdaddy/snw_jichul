# S&W 지출결의서 작성이

미리 인쇄된 지출결의서 용지(A5, 5칸·6칸 결재란)에 내용을 맞춰 찍어 주는 Windows 프로그램입니다.

- 작성이력 검색 → 불러오기 → 금액·날짜만 고쳐 인쇄
- 결재란 전결·사선 규칙 자동 처리, 프린터별 영점조정
- 엑셀 작성이력 가져오기·내보내기
- 실행할 때 새 버전이 있으면 알려 주고 자동 설치

## 설치

[Releases](../../releases/latest) 에서 `SnW_Jichul_Setup_x.y.z.exe` 를 받아 실행합니다. 관리자 권한은 필요 없습니다.
작성이력·설정은 `내 문서\S&W 지출결의서\지출결의서.db` 에 저장되며, 프로그램을 지워도 남습니다.

## 새 버전 배포 (관리자)

1. 코드 수정 후 `CHANGELOG.md` 맨 위에 `## 새버전` 과 바뀐 내용을 적고 커밋·푸시 (프로그램의 업데이트 이력에 표시됨)
2. 버전 태그를 올립니다.

   ```
   git tag v1.3.1
   git push origin v1.3.1
   ```

3. GitHub Actions 가 설치파일을 만들어 Release 에 올립니다 (약 5분).
4. 각 PC 의 프로그램이 다음 실행 때 "새 버전이 있습니다"라고 알려 줍니다.

이 PC 에서 직접 만들 때: `python tools/build.py` → `dist\SnW_Jichul_Setup_<버전>.exe`

## 폴더

| 경로 | 내용 |
|---|---|
| `app/` | 프로그램 소스 (PySide6) |
| `app/layout.py` | 용지 좌표 (실측 보정 기록 포함) |
| `installer/setup.iss` | 설치 프로그램 (Inno Setup) |
| `tools/build.py` | exe + 설치파일 빌드 |
| `.github/workflows/release.yml` | 태그 푸시 시 자동 빌드·Release |
