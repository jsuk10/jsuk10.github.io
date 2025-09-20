---
title: Asset Picker생성
tags: UE4.27 Slate
---

# Asset Picker생성

생성일: 2025년 8월 1일 오후 3:08

특정 에셋만 빠르게 볼 수 있는 기능인 Asset Picker창 제작 

![image.png](/assets/images/UE4.27/AssetPicker0.png)

# Asset Picker

컨텐츠 브라우저에서 특정 조건에 맞는 에셋을 보여주고, 선택이 가능한 Slate위젯

## 핵심 구성 요소

`FAssetPickerConfig`

IContentBrowserSingleton.h헤더에 정의되어 있음

- Asset Picker를 만들 때 넘겨주는 설정 구조체

어떤 에셋을 보여줄지, 선택 방식은 어떤지, 선택 시 콜백은 뭘 할지 정의

| 항목                                              | 설명                            | 예시                                                               |
| ----------------------------------------------- | ----------------------------- | ---------------------------------------------------------------- |
| `FAssetFilter Filter`                           | 보여줄 에셋 조건 (클래스 이름, 경로, 태그 등)  | `Filter.ClassNames.Add(UStaticMesh::StaticClass()->GetFName());` |
| `ESelectionMode::Type SelectionMode`            | 에셋 선택 모드 (단일 / 다중)            | `Single` / `Multi`                                               |
| `FOnAssetSelected OnAssetSelected`              | 단일 선택 시 호출되는 델리게이트            | 선택된 `FAssetData` 전달                                              |
| `FOnAssetsSelected OnAssetsSelected`            | 다중 선택 시 호출되는 델리게이트            | 여러 `FAssetData` 전달                                               |
| `FOnAssetDoubleClicked`, `FOnAssetEnterPressed` | 더블클릭 또는 엔터 입력 처리              |                                                                 |
| `InitialAssetViewType (List / Tile)`                                           | 초기 뷰 타입, 검색박스 포커스, 툴바 표시 여부 등 | `EAssetViewType::Type::List/Tile`                               |


디테일 패널 내에서 매쉬 선택시 동일하게 Asset Picker가 사용됨을 알 수 있다.

![image.png](/assets/images/UE4.27/AssetPicker1.png)

- ContentBrowserModule.Get().CreateAssetPicke로 만들 수 있다.

# 구현

## 1. 버튼 추가

[에디터 버튼 추가](에디터 버튼 추가.html) 을 참고하여 에디터에 버튼을 추가한다.

```cpp
void FTestEditor::AddToolbarButton(FToolBarBuilder& ToolbarBuilder)
{
	  ///...
	  
    ToolbarBuilder.AddToolBarButton(
        FUIAction(FExecuteAction::CreateRaw(this, &FTestEditor::OpenAssetPickerWindow)),
        NAME_None,
        INVTEXT("Asset Picker"),
        INVTEXT("Open Slate Asset Picker"),
        FSlateIcon(FEditorStyle::GetStyleSetName(), "LevelEditor.GameSettings")
    );
}
```

![image.png](/assets/images/UE4.27/AssetPicker2.png)

## 2. FAssetPickerConfig구성

```cpp
    FAssetPickerConfig AssetPickerConfig;
    // StaticMesh만 필터링
    AssetPickerConfig.Filter.ClassNames.Add(UStaticMesh::StaticClass()->GetFName());
    AssetPickerConfig.Filter.bRecursiveClasses = true;
    AssetPickerConfig.SelectionMode = ESelectionMode::Single;
    AssetPickerConfig.OnAssetSelected = FOnAssetSelected::CreateLambda([this](const FAssetData& SelectedAsset)
        {
            // 로그 출력
            UE_LOG(LogTemp, Log, TEXT("선택된 자산: %s"), *SelectedAsset.GetFullName());

            // Content Browser를 선택된 에셋이 들어있는 폴더로 이동/동기화
            FContentBrowserModule& CBModule = FModuleManager::LoadModuleChecked<FContentBrowserModule>("ContentBrowser");
            TArray<FAssetData> AssetsToSync;
            AssetsToSync.Add(SelectedAsset);
            CBModule.Get().SyncBrowserToAssets(AssetsToSync, true);
        });
    AssetPickerConfig.InitialAssetViewType = EAssetViewType::List;
```

- OnAssetSelected에 원하는 동작 바인딩

[GitHub Code](https://github.com/jsuk10/PracticetUnrealEngine/commit/2d5b48046f11d899e4149e1a5125969030ae15dd){:.button.button--outline-success.button--pill}

## 3. Asset Picker창 구현

ContentBrowser 모듈에 AssetPicker이 있으니 해당 가져옴

```cpp
// Asset Picker 위젯 생성
FContentBrowserModule& ContentBrowserModule = FModuleManager::LoadModuleChecked<FContentBrowserModule>("ContentBrowser");
TSharedRef<SWidget> AssetPickerWidget = ContentBrowserModule.Get().CreateAssetPicker(AssetPickerConfig);

```

Asset Picker을 보여줄 Window생성

```cpp
// Asset Picker을 보여줄 창 만들기
    PickerWindow = SNew(SWindow)
        .Title(INVTEXT("Slate Asset Picker"))
        .ClientSize(FVector2D(600, 400))
        .SupportsMinimize(false)
        .SupportsMaximize(false)
        [
            SNew(SBorder)
                .Padding(8)
                [
                    SNew(SVerticalBox)
                        + SVerticalBox::Slot()
                        .AutoHeight()
                        .Padding(0, 0, 0, 4)
                        [
                            SNew(STextBlock)
                                .Text(INVTEXT("Static Mesh 선택:"))
                                .Font(FCoreStyle::GetDefaultFontStyle("Regular", 14))
                        ]
                        + SVerticalBox::Slot()
                        .FillHeight(1.0f)
                        [
                            AssetPickerWidget
                        ]
                ]
        ];
        
        // 창 추가
        FSlateApplication::Get().AddWindow(PickerWindow.ToSharedRef());
```
[GitHub Code](https://github.com/jsuk10/PracticetUnrealEngine/commit/3323433392dcf64a5634ef39f8d2e88e82ec09d7){:.button.button--outline-success.button--pill}
