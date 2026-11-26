"""설정 > 사용방법: 프로그램 안에서 읽는 사용 안내서."""
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QTextBrowser, QVBoxLayout, QWidget

from ui_common import card

BLUE = "#1a73e8"

# (앵커, 목차 제목, 본문 HTML)
SECTIONS = [
    ("start", "1. 처음 한 번만 할 일", """
<p>설치하고 처음 켰을 때 아래 순서대로 한 번만 맞춰 두면, 그다음부터는 내용만 입력하고 [인쇄]를 누르면 됩니다.</p>
<ol>
<li><b>기본값 입력</b> — [설정 &gt; 프린터 · 기본값]
  <ul>
  <li><b>기본 수령인(성명)</b>: 새로 작성할 때 수령인 칸에 자동으로 들어갈 이름 (보통 본인 이름)</li>
  <li><b>최종결재자 성명</b>: 결재란 마지막 칸(대표이사·회장) 본인 이름. 그분 본인 건을 쓸 때 수령인에 자동으로 들어갑니다.</li>
  <li>입력한 뒤 <b>[저장]</b>을 꼭 누르세요.</li>
  </ul></li>
<li><b>양식 고르기</b> — 작성 화면 미리보기 위 첫 번째 칸
  <ul>
  <li><b>5칸</b>: 기존 용지 (담당 · 팀장 · 부서장 · 이사 · 대표이사)</li>
  <li><b>6칸</b>: 신규 용지 (담당 · 팀장 · 부서장 · 이사 · 사장 · 회장)</li>
  <li>가지고 있는 결의서 용지의 결재란 칸 수를 세어서 고르면 됩니다.</li>
  </ul></li>
<li><b>프린터 · 용지 고르기</b> — 양식 옆 칸 (자세한 내용은 <a href="#paper">9. 프린터 · 용지 · 영점 · 배율</a>)
  <ul>
  <li>잉크젯(캐논 등): <b>A5</b></li>
  <li>복합기(신도리코 등)에서 용지를 인식하지 못하면: <b>B6</b></li>
  </ul></li>
<li><b>시험 인쇄로 위치 맞추기</b> — [영점조정] → [시험 인쇄]
  <ul>
  <li>결의서 용지 대신 <b>빈 종이</b>를 넣고 시험 인쇄하면 양식 선과 글자가 같이 찍힙니다.</li>
  <li>찍힌 종이를 실제 결의서 용지와 겹쳐 불빛에 비춰 보고, 어긋난 만큼 ◀ ▶ ▲ ▼ 로 옮깁니다.</li>
  <li>크기가 다르면(작게 / 크게 찍힘) <b>배율</b>을 조정합니다.</li>
  </ul></li>
</ol>
<p class='tip'>프린터를 여러 대 쓰면 용지 · 영점 · 배율이 <b>프린터마다 따로</b> 저장됩니다. 프린터를 바꾸면 그 프린터에 맞춰 둔 값이 자동으로 적용됩니다.</p>
"""),
    ("screen", "2. 화면 구성", """
<table>
<tr><th>위치</th><th>내용</th></tr>
<tr><td>맨 위</td><td>[작성] · [설정] 메뉴. 오른쪽 [도움말]에서 업데이트 확인 · 시험 인쇄 · 데이터 폴더 열기 · 사용방법</td></tr>
<tr><td>왼쪽</td><td>입력칸 — <b>기본 정보</b>(계정과목 · 비고 · 지출처 · 금액 · 계산기), <b>내역(적요)</b>(내역 · 작성일 · 수령인), <b>결재란</b></td></tr>
<tr><td>가운데 위</td><td>양식 · 프린터 · 용지 · [영점조정] 과 [새로 작성] [저장] [인쇄] 버튼</td></tr>
<tr><td>가운데</td><td><b>미리보기</b> — 입력하는 즉시 실제 용지에 찍히는 모양 그대로 보여 줍니다.</td></tr>
<tr><td>가운데 아래</td><td><b>첨부파일</b> — 결의서 다음에 A4로 같이 인쇄할 서류</td></tr>
<tr><td>오른쪽</td><td><b>작성이력</b> — 지금까지 저장 · 인쇄한 결의서 목록, 검색 · 불러오기 · 삭제</td></tr>
</table>
<p class='tip'>미리보기와 작성이력 사이 경계선을 마우스로 끌면 폭을 바꿀 수 있고, 바꾼 폭은 다음에 켤 때도 그대로입니다.</p>
"""),
    ("write", "3. 지출결의서 작성", """
<p>종이에 써지는 순서대로 위에서부터 채우면 됩니다. 입력하는 동안 미리보기가 바로 바뀝니다.</p>
<h3>계정과목 · 비고</h3>
<ul>
<li><b>계정과목</b>: 직접 입력하거나 목록에서 고릅니다. 한 번 저장 · 인쇄한 계정과목은 목록에 쌓이고, 많이 쓴 순서로 위에 나옵니다.</li>
<li>목록에서 필요 없는 항목은 오른쪽 <b>✕</b> 를 누르면 목록에서만 빠집니다 (작성이력은 그대로).</li>
<li><b>비고</b>: 간단한 메모. 종이의 과목(科目) 줄 오른쪽 빈칸에 인쇄됩니다.</li>
</ul>
<h3>지출처</h3>
<ul>
<li>몇 글자만 치면 예전에 쓴 지출처가 자동완성으로 나옵니다.</li>
<li>자동완성에서 고르면, 계정과목이 비어 있을 때 그 지출처에 마지막으로 쓴 계정과목이 같이 들어갑니다.</li>
</ul>
<h3>금액 · VAT</h3>
<ul>
<li>숫자만 입력하면 쉼표(,)가 자동으로 붙고, 오른쪽에 <b>한글 금액</b>(금 ○○원정)이 표시됩니다.</li>
<li><b>VAT 포함</b>을 체크하면 내역의 금액 줄에 "(VAT 포함)"이 붙습니다.</li>
<li>내역에 <b>"2) 금액 :"</b> 줄이 있으면 위에 입력한 금액이 그 줄에 자동으로 들어갑니다.</li>
</ul>
<h3>계산기</h3>
<ul>
<li>식을 쓰면 [금액에 넣기] 위에 결과가 바로 보입니다. 예) <code>380,000*4</code>, <code>12000+8500</code></li>
<li><b>Enter</b>: 결과를 금액칸에 넣기 · <b>Shift+Enter</b>: 줄바꿈</li>
<li>줄을 바꿔 숫자를 쓰면 모두 더합니다 (영수증 여러 장 합계 낼 때 편리).</li>
<li>×, ÷, x 도 곱하기 · 나누기로 알아듣고, 괄호도 쓸 수 있습니다.</li>
</ul>
<h3>내역 (적요)</h3>
<ul>
<li><b>[기본 틀]</b>을 누르면 "1) 내역 / 2) 금액 / 3) 첨부" 틀이 들어갑니다.</li>
<li><b>글자크기</b>(8~15, 기본 11)를 줄이면 더 많은 줄이 들어갑니다. 아래에 지금 몇 줄을 썼고 몇 줄까지 들어가는지 표시됩니다.</li>
<li>들어가는 줄 수를 넘기면 인쇄할 때 한 번 더 물어봅니다.</li>
</ul>
<h3>작성일 · 수령인</h3>
<ul>
<li><b>작성일</b>은 오늘 날짜로 자동 입력됩니다. 바꾸면 결재란 결재일도 모두 같은 날짜로 바뀝니다.</li>
<li><b>년월일 인쇄 안 함</b>: 날짜를 손으로 쓰려고 할 때 체크하면 작성일 · 결재일이 인쇄되지 않습니다.</li>
<li><b>수령인</b>: 기본 수령인이 자동으로 들어가고, 예전에 쓴 이름은 목록에서 고를 수 있습니다 (✕ 로 목록에서 빼기).</li>
</ul>
"""),
    ("approval", "4. 결재란 (결재일 · 사선 · 전결)", """
<p>결재란은 실제 용지처럼 칸이 가로로 놓여 있고, 칸마다 <b>결재일 · 사선 · 전결</b>을 정합니다.</p>
<table>
<tr><th>항목</th><th>설명</th></tr>
<tr><td>결재일</td><td>기본은 모두 작성일. 칸을 눌러 달력에서 칸마다 따로 바꿀 수 있습니다. <b>[결재일 = 작성일]</b>을 누르면 모두 작성일로 되돌아갑니다.</td></tr>
<tr><td>사선</td><td>체크한 칸에 사선(／)이 그어지고 날짜는 인쇄되지 않습니다.</td></tr>
<tr><td>전결</td><td>체크한 칸에 '전결'이 찍히고, 그 칸과 마지막 칸 사이는 <b>자동으로 사선</b>이 그어집니다. (5칸: 부서장·이사, 6칸: 부서장·이사·사장 칸에서 가능)</td></tr>
<tr><td>(마지막 칸) 전결</td><td>대표이사 · 회장 본인 건. 마지막 칸만 도장 칸으로 두고 나머지 칸은 모두 사선. 최종결재자 성명을 설정해 두면 수령인도 그 이름으로 바뀝니다.</td></tr>
</table>
<p class='tip'>마지막 칸(대표이사 · 회장)은 항상 도장 칸이라 사선 · 전결을 체크할 수 없습니다.<br>
사선 · 전결 · 본인 건 표시는 저장 · 인쇄할 때 작성이력에 같이 저장돼, 불러오면 그대로 다시 체크됩니다. (결재일은 불러온 날짜로)</p>
"""),
    ("image", "5. 이미지(엑셀 표 등) 붙이기", """
<ol>
<li>엑셀에서 표를 선택하고 <b>Ctrl+C</b> (또는 캡처 도구로 화면 캡처)</li>
<li>지출이에서 <b>미리보기를 한 번 클릭</b>한 뒤 <b>Ctrl+V</b></li>
<li>올라간 이미지를 <b>드래그</b>해서 원하는 자리로 옮깁니다.</li>
<li>크기 조절: <b>모서리 파란 점</b> = 비율 유지 · <b>변 가운데 흰 점</b> = 가로나 세로만</li>
<li>지우려면 이미지를 클릭하고 <b>Delete</b></li>
</ol>
<p class='tip'>입력칸(내역 등)에 커서가 있을 때 Ctrl+V 를 누르면 글자로 붙습니다. 이미지로 붙이려면 먼저 미리보기를 클릭하세요.<br>
붙인 이미지는 작성이력에 같이 저장돼, 불러오면 같은 자리에 다시 나옵니다.</p>
"""),
    ("attach", "6. 첨부파일 (A4로 같이 인쇄)", """
<p>세금계산서 · 견적서처럼 매번 결의서와 같이 내는 서류(PDF · 그림)를 붙여 두면, 인쇄할 때 결의서 다음에 <b>A4로 이어서</b> 나옵니다.</p>
<ul>
<li><b>[추가]</b> → <b>파일에서 찾아 추가</b>, 또는 <b>보관함에서</b> 바로 고르기. 파일을 첨부파일 칸으로 끌어다 놓아도 됩니다.</li>
<li><b>체크</b>를 끄면 붙여만 두고 인쇄는 하지 않습니다.</li>
<li><b>[보기]</b>: 붙은 파일 모두 열기 (하나만 볼 때는 파일 이름 더블클릭)</li>
<li><b>[삭제]</b>: 이 결의서에서만 빼기 (보관함에는 남아 있어 다시 붙일 수 있음)</li>
<li>자주 쓰는 파일은 [설정 &gt; 첨부파일 관리]에 등록해 두면 [추가 &gt; 보관함]에서 바로 고를 수 있습니다. 이름 바꾸기 · 삭제도 여기서 합니다.</li>
</ul>
<p class='tip'>첨부파일은 결의서와 같은 프린터로, 용지만 A4로 바꿔 나갑니다. 복합기라면 A4 용지함에서 나옵니다.</p>
"""),
    ("save", "7. 저장 · 인쇄 · 새로 작성", """
<table>
<tr><th>버튼</th><th>단축키</th><th>하는 일</th></tr>
<tr><td><b>인쇄</b></td><td>Ctrl+P</td><td>결의서(+ 첨부파일)를 인쇄하고 <b>작성이력에 자동 저장</b></td></tr>
<tr><td><b>저장</b></td><td>Ctrl+S</td><td>인쇄하지 않고 작성이력에만 저장</td></tr>
<tr><td><b>새로 작성</b></td><td>Ctrl+N</td><td>입력칸을 모두 비우고 오늘 날짜로 새로 시작</td></tr>
</table>
<ul>
<li>작성이력에서 <b>불러온 뒤 고쳐서 [저장]</b>하면 새로 쌓이지 않고 <b>그 이력에 덮어씁니다</b>.</li>
<li>완전히 같은 내용은 두 번 저장되지 않습니다 (중복 방지).</li>
<li>인쇄 대화상자(용지함 · 매수 선택)가 필요하면 [설정 &gt; 프린터 · 기본값]에서 "인쇄할 때마다 인쇄 대화상자 띄우기"를 켜세요.</li>
</ul>
"""),
    ("history", "8. 작성이력 (검색 · 불러오기 · 삭제)", """
<ul>
<li><b>검색</b>: 오른쪽 위 검색칸에 지출처 · 내역 · 금액 일부를 입력 (Ctrl+F 로 바로 이동). <b>↓</b> 키를 누르면 목록으로 내려갑니다.</li>
<li><b>불러오기</b>: 목록에서 <b>더블클릭</b> 또는 <b>Enter</b>. 내용 · 이미지 · 첨부파일 · 결재 사선/전결이 그대로 채워지고, 날짜는 <b>오늘</b>로 바뀝니다. 금액칸에 커서가 가 있어 금액만 고쳐 바로 인쇄하기 좋습니다.</li>
<li><b>삭제</b>: 고른 뒤 [삭제] 또는 <b>Delete</b> 키. Ctrl · Shift 를 누른 채 클릭하면 여러 건을 한꺼번에 고를 수 있습니다 (합계 금액도 확인 창에 표시).</li>
<li>열 제목 경계를 끌면 열 폭을 바꿀 수 있습니다.</li>
</ul>
<p class='tip'>[설정 &gt; 프린터 · 기본값]에서 "이력을 불러올 때 20만원 이하면 부서장 전결 자동 체크"를 켜면, 20만원 이하 이력을 불러올 때 부서장 전결이 자동으로 체크됩니다. (결재 표시가 저장돼 있는 이력은 저장된 표시가 먼저입니다)</p>
"""),
    ("paper", "9. 프린터 · 용지 · 영점 · 배율", """
<h3>용지 (A5 / B6)</h3>
<p>결의서 용지는 실제 크기가 약 <b>130 × 190mm</b>로, 정식 A5(148 × 210mm)보다 조금 작습니다.</p>
<table>
<tr><th>용지</th><th>이럴 때</th></tr>
<tr><td><b>A5</b></td><td>잉크젯(캐논 등) — 결의서 전용 용지함에 넣고 그대로 인쇄. 지금까지와 같습니다.</td></tr>
<tr><td><b>B6</b></td><td>복합기(신도리코 등)가 A5로 보내면 "일치하는 용지 크기가 없습니다"를 띄우거나 급지를 못 할 때</td></tr>
</table>
<p>용지는 <b>프린터마다 따로</b> 저장됩니다. 프린터 칸에서 그 프린터를 먼저 고른 뒤 용지를 바꾸세요.</p>

<h3>영점조정 (위치)</h3>
<ol>
<li>미리보기 위 <b>[영점조정]</b>을 누릅니다.</li>
<li><b>[시험 인쇄]</b> — 빈 종이에 양식 선과 글자가 같이 찍힙니다.</li>
<li>실제 결의서 용지와 겹쳐 보고 어긋난 방향의 <b>반대</b>로 옮깁니다.<br>
    예) 출력물이 오른쪽으로 1mm 밀렸으면 ◀ 를 1mm 만큼</li>
<li>한 번에 이동할 양은 0.1 / 0.5 / 1mm 중에서 고르고, 숫자칸에 직접 입력해도 됩니다.</li>
<li>다 맞췄으면 <b>[확인]</b>을 눌러야 저장됩니다. <b>[취소] · Esc · 창 닫기</b>를 누르면 바꾼 값은 버리고 창을 열기 전 값으로 돌아갑니다.<br>
    (창 안에서 [시험 인쇄]는 지금 바꾼 값으로 찍혀서, 확인 전에 미리 찍어 볼 수 있습니다)</li>
</ol>

<h3>배율 (크기)</h3>
<ul>
<li>글자 · 칸이 양식보다 <b>작게(축소)</b> 찍히면 100% 보다 <b>크게</b>, <b>크게</b> 찍히면 <b>작게</b> 합니다. 0.5% 단위로 맞출 수 있습니다.</li>
<li>복합기에서 B6 로 찍었을 때 작게 나오면 <b>115%</b> 근처부터 시험해 보세요.</li>
<li>배율은 왼쪽 위를 기준으로 커지므로, <b>배율을 먼저</b> 맞추고 <b>위치를 나중에</b> 맞추는 것이 편합니다.</li>
<li>B6 용지는 세로가 182mm 라 실제 용지(약 190mm)의 아래쪽 8mm 정도에는 인쇄되지 않습니다. 배율을 키운 뒤 결재란 날짜가 잘리지 않는지 확인하세요.</li>
</ul>
<p class='tip'>[0점으로]를 누르면 위치와 배율이 모두 처음 값(0mm, 100%)으로 돌아갑니다.<br>
영점조정 버튼에 지금 값이 표시됩니다. 예) <code>영점조정 ◀ 1.0 mm 115%</code></p>

<h3>복합기(신도리코 등) 추가 설정</h3>
<ul>
<li>수동급지대(바이패스)에 결의서 용지를 넣고, 복합기 패널에서 그 급지대 용지를 <b>B6</b>(또는 사용자 정의 크기)로 등록해 두세요.</li>
<li>Windows 에 같은 복합기를 하나 더 추가해 이름을 "(결의서용)"처럼 붙이고, 그 프린터의 기본 급지를 <b>수동 트레이</b>로 해 두면 A4 문서와 섞이지 않아 편합니다.</li>
</ul>
"""),
    ("coord", "10. 좌표 설정 (칸별 위치 · 글자크기)", """
<p>영점조정은 <b>전체</b>를 한꺼번에 옮기고, 좌표 설정은 <b>칸 하나씩</b> 옮깁니다. 영점을 맞췄는데도 특정 칸(예: 금액만)이 어긋날 때 씁니다.</p>
<ol>
<li>[설정 &gt; 좌표 설정]에서 항목(지출처 · 금액 · 내역 등)을 고르면 오른쪽 미리보기에 파란 테두리로 표시됩니다.</li>
<li>화살표나 숫자로 위치를 옮기고, 글자크기도 칸마다 바꿀 수 있습니다.</li>
<li>[시험 인쇄]로 확인한 뒤 <b>[저장]</b>. 저장하지 않고 나가면 한 번 물어봅니다.</li>
<li>[선택 초기화] · [전체 초기화]로 처음 값으로 되돌릴 수 있습니다.</li>
</ol>
"""),
    ("data", "11. 데이터 · 백업 · 엑셀", """
<ul>
<li>작성이력과 설정은 <b>데이터 파일 하나</b>에 저장됩니다. 위치는 [설정 &gt; 데이터]에서 볼 수 있고, [폴더 열기]로 바로 열립니다.</li>
<li>프로그램을 업데이트하거나 다시 설치해도 작성이력 · 설정은 <b>그대로</b> 남습니다.</li>
<li><b>[백업 만들기]</b>: 원하는 곳에 데이터 파일 복사본을 저장합니다. 가끔 USB 나 공유폴더에 백업해 두세요.</li>
<li><b>엑셀 가져오기</b>: 예전 엑셀 결의서나 다른 부서 엑셀의 작성이력을 불러옵니다. 열(날짜 · 지출처 · 금액 · 내역 등)을 자동으로 맞춰 주고, 이미 있는 이력은 건너뜁니다.</li>
<li><b>엑셀 내보내기</b>: 전체 작성이력을 엑셀 파일로 저장합니다 (집계 · 보고용).</li>
</ul>
<p class='tip'><b>새 PC로 옮길 때</b>: 예전 PC에서 [백업 만들기]로 파일을 만들고, 새 PC에 지출이를 설치한 뒤 [데이터 &gt; 폴더 열기]로 연 폴더에 그 파일을 같은 이름으로 덮어쓰세요 (지출이를 끈 상태에서).</p>
"""),
    ("update", "12. 업데이트", """
<ul>
<li>프로그램을 켤 때 새 버전이 있는지 자동으로 확인하고, 있으면 안내창이 뜹니다. [예]를 누르면 받아서 설치하고 다시 켜집니다.</li>
<li>직접 확인: [설정 &gt; 업데이트 &gt; 지금 확인] 또는 [도움말 &gt; 업데이트 확인]</li>
<li>[업데이트 이력]에서 버전별로 무엇이 바뀌었는지 볼 수 있습니다.</li>
<li>회사 인터넷 사정으로 확인이 안 되면 상태칸에 이유가 표시됩니다. 나중에 다시 시도하면 됩니다.</li>
</ul>
"""),
    ("keys", "13. 단축키", """
<table>
<tr><th>단축키</th><th>기능</th></tr>
<tr><td>Ctrl+P</td><td>인쇄 (작성이력 자동 저장)</td></tr>
<tr><td>Ctrl+S</td><td>저장</td></tr>
<tr><td>Ctrl+N</td><td>새로 작성</td></tr>
<tr><td>Ctrl+F</td><td>작성이력 검색칸으로</td></tr>
<tr><td>Ctrl+1 / Ctrl+2</td><td>작성 화면 / 설정 화면</td></tr>
<tr><td>Ctrl+V</td><td>(미리보기 클릭 후) 클립보드 이미지 붙이기</td></tr>
<tr><td>↓ (검색칸에서)</td><td>작성이력 목록으로 이동</td></tr>
<tr><td>Enter (작성이력에서)</td><td>불러오기</td></tr>
<tr><td>Delete (작성이력에서)</td><td>선택한 이력 삭제</td></tr>
<tr><td>Enter / Shift+Enter (계산기)</td><td>금액에 넣기 / 줄바꿈</td></tr>
</table>
"""),
    ("faq", "14. 이럴 땐 이렇게 (문제 해결)", """
<h3>A4 크기로 크게 찍혀요 / "용지 크기 확인" 창이 떠요</h3>
<p>프린터 드라이버에서 용지가 A4로 고정돼 있거나 '용지에 맞춤(확대/축소)'이 켜져 있는 경우입니다. 확인 창에서 [예]를 누르면 프린터 '인쇄 기본 설정' 창이 열리니, 용지 크기를 A5(또는 B6)로 바꾸고 맞춤 인쇄를 끄세요.</p>
<h3>복합기에서 "일치하는 용지 크기가 없습니다"가 떠요</h3>
<p>용지를 <b>B6</b>로 바꾸고, 복합기 급지대에도 같은 크기를 등록하세요. (<a href="#paper">9번</a> 참고)</p>
<h3>B6 로 찍었더니 작게(축소돼) 나와요</h3>
<p>[영점조정]에서 <b>배율</b>을 올리세요. 115% 근처부터 시험 인쇄하며 맞춥니다.</p>
<h3>전체가 조금씩 밀려요</h3>
<p>[영점조정]에서 시험 인쇄 후 ◀ ▶ ▲ ▼ 로 맞춥니다. 프린터마다 따로 저장됩니다.</p>
<h3>특정 칸만 어긋나요</h3>
<p>[설정 &gt; 좌표 설정]에서 그 칸만 옮기세요. (<a href="#coord">10번</a> 참고)</p>
<h3>내역이 칸을 넘쳐요</h3>
<p>내역 아래 <b>글자크기</b>를 줄이면 더 많은 줄이 들어갑니다. 빈 줄을 줄이는 것도 방법입니다.</p>
<h3>Ctrl+V 를 눌렀는데 이미지가 아니라 글자가 붙어요</h3>
<p>입력칸에 커서가 있으면 글자로 붙습니다. <b>미리보기를 한 번 클릭</b>한 뒤 Ctrl+V 하세요.</p>
<h3>계정과목 · 수령인 목록에 잘못 쓴 이름이 있어요</h3>
<p>목록을 펼쳐 그 항목 오른쪽 <b>✕</b> 를 누르면 목록에서 빠집니다. (작성이력은 지워지지 않음)</p>
<h3>실수로 이력을 지웠어요</h3>
<p>삭제한 이력은 되돌릴 수 없습니다. [백업 만들기]로 받아 둔 파일이 있으면 그 파일로 되돌릴 수 있으니, 가끔 백업해 두세요.</p>
"""),
]

CSS = f"""
body {{ font-size: 10pt; color: #202124; line-height: 160%; }}
h2 {{ font-size: 14pt; color: {BLUE}; margin: 26px 0 8px 0; }}
h3 {{ font-size: 11pt; color: #202124; margin: 14px 0 4px 0; }}
p {{ margin: 4px 0 8px 0; }}
li {{ margin: 3px 0; }}
table {{ border-collapse: collapse; margin: 6px 0 10px 0; }}
th {{ background: #e8f0fe; color: #174ea6; padding: 6px 10px; text-align: left; }}
td {{ padding: 6px 10px; vertical-align: top; }}
code {{ background: #f1f3f4; color: #c5221f; }}
a {{ color: {BLUE}; text-decoration: none; }}
.tip {{ background: #fef7e0; color: #5f4b00; padding: 8px 12px; }}
"""


def guide_html():
    parts = [f"<html><head><style>{CSS}</style></head><body>",
             "<p style='color:#5f6368'>지출이로 지출결의서를 작성 · 인쇄하는 방법입니다. "
             "왼쪽 목차를 누르면 그 내용으로 바로 이동합니다.</p>"]
    for key, title, body in SECTIONS:
        # QTextBrowser 는 표 테두리를 CSS 로 못 그려서 border 속성으로
        body = body.replace("<table>", "<table border='1' cellspacing='0' cellpadding='6' "
                                       "style='border-color:#dadce0' width='100%'>")
        body = body.replace("<p class='tip'>", "<table width='100%' cellpadding='10' cellspacing='0' "
                                               "style='margin:8px 0 6px 0'><tr><td class='tip'>💡 ")
        body = body.replace("<code>", "<span style='background:#f1f3f4; color:#c5221f'>&nbsp;").replace("</code>", "&nbsp;</span>")
        parts.append(f"<a name='{key}'></a><h2>{title}</h2>{_close_tips(body)}")
    parts.append("<p style='color:#9aa0a6; margin-top:30px'>궁금한 점이나 고쳤으면 하는 점은 담당자에게 알려 주세요.</p>")
    parts.append("</body></html>")
    return "".join(parts)


def _close_tips(body):
    """<p class='tip'> 를 표로 바꾼 곳의 닫는 </p> 를 </td></tr></table> 로."""
    out, i = [], 0
    marker = "<td class='tip'>💡 "
    while True:
        j = body.find(marker, i)
        if j < 0:
            out.append(body[i:]); break
        k = body.find("</p>", j)
        out.append(body[i:k]); out.append("</td></tr></table>")
        i = k + len("</p>")
    return "".join(out)


class GuidePanel(QWidget):
    """설정 > 사용방법: 왼쪽 목차 + 오른쪽 본문."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(12)

        self.toc = QListWidget(); self.toc.setObjectName("SideNav"); self.toc.setFixedWidth(230)
        from PySide6.QtCore import Qt
        self.toc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for key, title, _ in SECTIONS:
            it = QListWidgetItem(title); it.setData(256, key); self.toc.addItem(it)
        self.toc.currentRowChanged.connect(lambda r: self.go(SECTIONS[r][0]) if r >= 0 else None)
        tw = QWidget(); tv = QVBoxLayout(tw); tv.setContentsMargins(0, 0, 0, 0); tv.addWidget(self.toc)
        root.addWidget(card(tw, "목차", margins=(8, 8, 8, 8)))

        self.view = QTextBrowser(); self.view.setOpenLinks(False)
        self.view.setStyleSheet("QTextBrowser { border: none; background: transparent; }")
        self.view.anchorClicked.connect(self._link)
        self.view.setHtml(guide_html())
        hint = QLabel("설정 메뉴에서 언제든 다시 볼 수 있습니다"); hint.setObjectName("Hint")
        root.addWidget(card(self.view, "사용방법", extra=[hint]), 1)

    def go(self, key):
        self.view.scrollToAnchor(key)

    def _link(self, url):
        if url.hasFragment():
            key = url.fragment()
            keys = [k for k, _, _ in SECTIONS]
            if key in keys:
                self.toc.blockSignals(True); self.toc.setCurrentRow(keys.index(key)); self.toc.blockSignals(False)
            self.go(key)
