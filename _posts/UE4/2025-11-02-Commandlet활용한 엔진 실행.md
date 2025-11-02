---
title: Commandlet활용한 엔진 실행
key: Commandlet활용한 엔진 실행
tags: UE4.27
---

# Commandlet활용한 엔진 실행

생성일: 2025-11-02

## ✅ Commandlet이란?

Commandlet은 **언리얼 엔진 에디터를 실행하지 않고도 명령줄 환경에서 작업을 수행할 수 있는 실행 모듈**입니다.  
주로 에디터 UI가 불필요한 반복 작업, 배치 처리, 자동화 환경에서 활용됩니다.

> 에디터 로딩 없이 UE 내부 API(UObject, Assets 등)에 접근할 수 있는 점이 일반 유틸리티 스크립트와의 차별점입니다.

---

## ✅ 왜 Commandlet을 사용하는가?

### 1) 빠른 실행 속도

에디터 UI 로딩 과정 없이 동작하므로 초기 실행 지연이 거의 없습니다.  
대형 프로젝트일수록 효과가 큽니다.

### 2) 자동화 및 스크립트 친화적

- CI/CD (Jenkins, GitHub Actions)
- Python, PowerShell, Shell 스크립트

### 3) Headless 서버 환경에서 동작

그래픽 환경이 없는 서버, Docker 환경에서도 동작합니다.

### 4) 절차 자동화 및 일관성 보장

개발자 환경과 무관하게 동일 파이프라인 유지 가능

---

# 1. UCommandlet을 상속한 클래스 제작

UCommandlet을 상속한 클래스를 제작 한다.

파라미터로 넘긴 인자를 얻는 방법은 크게 두가지가 있다.

1. `FCommandLine::Get()` 사용

   여러 인자가 들어오므로 `FCommandLine::Parse`으로 나누는게 좋다

2. `Main(const FString& Params)` 에 들어오는 Params사용

| 항목                       | 내용                                                                            |
| -------------------------- | ------------------------------------------------------------------------------- |
| `Params`                   | `-run=Commandlet명` **뒤에 오는 문자열 그대로** 전달됨 (언리얼이 필터링한 부분) |
| `FCommandLine::Get()`      | **실행 전체 커맨드라인 원본 문자열**                                            |
| `FCommandLine::Parse` 결과 | 전체 커맨드라인을 토큰(Tokens)과 스위치(Switches)로 분석한 결과                 |

## Commandlet 클래스 구현

```cpp
// TestCommandlet.h
#pragma once

#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"
#include "TestCommandlet.generated.h"

UCLASS(Config = Editor)
class UTestCommandlet : public UCommandlet
{
    GENERATED_BODY()

public:
    virtual int32 Main(const FString& Params) override;
};

```

```cpp
// TestCommandlet.cpp
#include "TestCommandlet.h"
#include "Misc/CommandLine.h"
#include "Misc/OutputDevice.h"
#include "Misc/Paths.h"
#include "Misc/MessageDialog.h"
#include "HAL/PlatformProcess.h"

int32 UTestCommandlet::Main(const FString& Params)
{
    TArray<FString> Tokens, Switches;
    FCommandLine::Parse(FCommandLine::Get(), Tokens, Switches);

    FString DialogText;
    DialogText += TEXT("=== Commandlet Input Summary ===\n\n");
    DialogText += FString::Printf(TEXT("Params:\n%s\n\n"), *Params);
    DialogText += FString::Printf(TEXT("Full CommandLine:\n%s\n"), FCommandLine::Get());
    DialogText += TEXT("\n-- Tokens --\n");
    for (int32 i = 0; i < Tokens.Num(); ++i)
        DialogText += FString::Printf(TEXT("[%d] %s\n"), i, *Tokens[i]);
    DialogText += TEXT("\n-- Switches --\n");
    for (int32 i = 0; i < Switches.Num(); ++i)
        DialogText += FString::Printf(TEXT("[%d] -%s\n"), i, *Switches[i]);
    const FText TitleText = FText::FromString(TEXT("Commandlet Parameters"));

    FMessageDialog::Open(
        EAppMsgType::Ok,
        FText::FromString(DialogText),
        &TitleText
    );

    return 0;
}
```

---

# 2. Commandlet 실행하기

### CMD 실행 예시

```cmd
"C:\UE\Engine\Binaries\Win64\UE4Editor-Cmd.exe" "C:\Game\TestProject\Test.uproject" -run=TestCommandlet -Key=Value Foo Bar
```

### Unreal VS에서 실행하기

Unreal 에서는 Unreal VS라는 Visual Studio의 확장을 지원하여 이를 설치하여 테스트 할 수도 있다.

`Engine\Extras\UnrealVS`에서 해당하는 버전을 찾으면 된다.

![image.png](/assets/images/UE4.27/Commandlet.png)

설치후 아래와 같이 인자를 줄 수 있다.

![image.png](/assets/images/UE4.27/Commandlet_1.png)

![image.png](/assets/images/UE4.27/Commandlet_2.png)

### 실행 결과

![image.png](/assets/images/UE4.27/Commandlet_3.png)

---

# 3. Python 외부 런처 예시

이를 통해 파이썬으로 필요한 Token, Switch를 설정하고 이를 넘기면 이전 단계에서 만든 Commandlet을 통해 입맛대로 실행하면 된다.

- 패키징을 통해 exe파일로 만들거나, gui를 추가해서 툴로 만들면 사용자의 편의성이 올라가고 작업 시간이 단축된다.

```python
import os
import subprocess
from pathlib import Path
from typing import Optional

# ===== 공용 유틸 =====
def _message_box(title: str, message: str) -> None:
    """Windows 메시지 박스. 실패 시 콘솔로 대체."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONHAND
    except Exception:
        print(f"[POPUP] {title}: {message}")

def _first_uproject_in(directory: Path) -> Optional[Path]:
    """지정 폴더에서 첫 번째 .uproject 반환."""
    matches = list(directory.glob("*.uproject"))
    return matches[0] if matches else None

def _pick_ue4_editor(bin_dir: Path) -> Optional[Path]:
    """Cmd 우선 선택, 없으면 GUI 에디터 반환."""
    cmd = bin_dir / "UE4Editor-Cmd.exe"
    if cmd.exists():
        return cmd
    gui = bin_dir / "UE4Editor.exe"
    if gui.exists():
        return gui
    return None

# ===== 핵심 실행기 =====
def run_commandlet(
    commandlet_name: str,
    args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> int:
    """
    현재 작업 디렉터리 에서 .uproject 탐색
    현재 작업 디렉터리에서 ue4/Engine/Binaries/Win64 하위에서 UE4Editor(-Cmd).exe 탐색
    필요하면 아래 경로를 변경하면 된다.
    """
    current = Path.cwd()
    parent = current.parent

    # 1) 부모 폴더에서 .uproject 찾기
    uproject = _first_uproject_in(current)
    if not uproject:
        _message_box("UPROJECT 없음", f".uproject 파일을 찾을 수 없습니다.\n검색 경로: {current}")
        raise FileNotFoundError(f".uproject not found in {current}")

    # 2) 부모 폴더에서 ue4\\Engine\\Binaries\\Win64 지정
    ue4_bin_dir = Path(os.path.join(str(parent),"ue4","Engine","Binaries","Win64"))
    if not ue4_bin_dir.exists():
        _message_box("UE4 BIN 폴더 없음", f"UE4 BIN 폴더가 없습니다.\n기대 경로: {ue4_bin_dir}")
        raise FileNotFoundError(f"UE4 bin not found: {ue4_bin_dir}")

    # 3) 실행 파일 선택: UE4Editor-Cmd.exe → UE4Editor.exe
    ue4_exec = _pick_ue4_editor(ue4_bin_dir)
    if not ue4_exec:
        _message_box(
            "UE4 실행 파일 없음",
            f"UE4Editor-Cmd.exe 또는 UE4Editor.exe가 없습니다.\n경로: {ue4_bin_dir}"
        )
        raise FileNotFoundError(f"No UE4 editor executable in {ue4_bin_dir}")

    # 4) 명령 구성 및 실행
    cmd = [str(ue4_exec), str(uproject), f"-run={commandlet_name}"]
    if args:
        cmd.extend(args)

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")

    code = proc.wait()
    print(f"\n[UE4 Commandlet ExitCode] {code}")
    return code

if __name__ == "__main__":
    # 예시
    COMMANDLET = "TestCommandlet"
    ARGS = ["-Key=Value", "Foo", "Bar"]
    run_commandlet(COMMANDLET, ARGS)

```

위와 같이 만든다면 아래 cmd에서 테스트 해본다.
![image.png](/assets/images/UE4.27/Commandlet_4.png)

---

## Code

[Git](https://github.com/jsuk10/PracticetUnrealEngine/commit/189534f158678414068215bf4514ff7b652a5a7d)

## 📎 참고 문서

- [Commandlets – Unreal Engine 문서](https://dev.epicgames.com/documentation/ko-kr/unreal-engine/command-line-arguments-in-unreal-engine)
- [UnrealVS – Unreal Engine 문서](https://dev.epicgames.com/documentation/ko-kr/unreal-engine/using-the-unrealvs-extension-for-unreal-engine-cplusplus-projects?application_version=5.5)

---
