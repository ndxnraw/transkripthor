import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    visible: true
    width: 1120
    height: 800
    minimumWidth: 560
    minimumHeight: 480
    title: "ND TranskripThor · " + backend.version
    color: p.bg
    property var p: backend.colors
    property bool forceClose: false
    property int queueSelection: -1
    function t(key) { return backend.t(key) }
    function pageIndex(name) { return ({home:0, editor:1, models:2, settings:3, diagnostics:4, log:5})[name] || 0 }
    Material.theme: backend.settings.theme === "dark" ? Material.Dark : Material.Light
    Material.primary: p.card
    Material.background: p.card
    Material.foreground: p.text
    Material.accent: p.blue
    palette.window: p.bg
    palette.base: p.field
    palette.text: p.text
    palette.windowText: p.text
    palette.buttonText: p.text
    palette.highlight: p.blue
    palette.highlightedText: p.accent_text
    font.family: "Segoe UI"
    onClosing: function(event) { event.accepted = forceClose || backend.request_close() }

    component Caption: Label {
        color: window.p.text
        font.pixelSize: 14
        wrapMode: Text.Wrap
    }
    component Panel: Rectangle {
        color: window.p.card
        radius: window.p.contrast ? 0 : 12
        border.color: window.p.border
        border.width: 1
    }
    component ReadOnlyText: TextArea {
        readOnly: true
        selectByMouse: true
        persistentSelection: true
        wrapMode: TextEdit.Wrap
        color: window.p.text
        selectionColor: window.p.blue
        selectedTextColor: window.p.accent_text
        font.pixelSize: 14
        background: Rectangle { color: window.p.field }
    }

    header: ToolBar {
        background: Rectangle { color: window.p.card; border.color: window.p.border }
        contentHeight: 64
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18; anchors.rightMargin: 18
            spacing: 12
            Image { source: backend.logo; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
            Caption { text: "ND TranskripThor"; font.pixelSize: window.width < 700 ? 18 : 22; font.bold: true; Layout.fillWidth: true; maximumLineCount: 1; elide: Text.ElideRight }
            ActionButton { objectName: "backButton"; text: window.t("qml.back"); visible: backend.view !== "home"; onClicked: backend.show("home") }
            ActionButton { text: "⋯"; Accessible.name: window.t("studio.options"); onClicked: appMenu.popup() }
        }
    }
    Menu {
        id: appMenu
        MenuItem { text: window.t("project.open"); enabled: !backend.busy; onTriggered: backend.choose_project() }
        MenuItem { text: window.t("qml.return_editor"); enabled: backend.projectName.length > 0; onTriggered: backend.show("editor") }
        MenuSeparator {}
        MenuItem { text: window.t("studio.advanced"); onTriggered: backend.show("settings") }
        MenuItem { text: window.t("ui_layout.labels.models"); enabled: !backend.busy; onTriggered: backend.show("models") }
        MenuItem { text: window.t("data.title"); enabled: !backend.busy; onTriggered: backend.inspect_data() }
        MenuItem { text: window.t("ui_layout.build_ui.activity_log"); onTriggered: backend.show("log") }
        MenuItem { text: window.t("ui_layout.build_ui.open_results"); onTriggered: backend.open_output() }
        MenuSeparator {}
        MenuItem { text: window.t("qml.change_theme"); onTriggered: backend.toggle_theme() }
        MenuItem { text: window.t("about.title"); onTriggered: aboutDialog.open() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: window.width < 700 ? 12 : 20
        spacing: 12
        StackLayout {
            id: workspace
            objectName: "workspace"
            currentIndex: window.pageIndex(backend.view)
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                spacing: 12
                Panel {
                    objectName: "dropSurface"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(parent.width-40, 680)
                        spacing: 18
                        visible: backend.queueCount === 0
                        Caption { text: window.t("studio.title"); font.pixelSize: window.width < 700 ? 25 : 32; font.bold: true; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                        Caption { text: window.t("studio.description"); color: window.p.muted; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                        ActionButton { objectName: "addFilesButton"; text: window.t("ui_layout.build_ui.add_recordings"); primary: true; enabled: !backend.transcribing; Layout.alignment: Qt.AlignHCenter; onClicked: backend.add_files() }
                        Caption { text: window.t("file_drop.init.drop_files_in_this_recording_area_or_use_add"); color: window.p.muted; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                    }
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 16
                        visible: backend.queueCount > 0
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: window.t("workspace.queue") + " · " + backend.queueCount; font.bold: true; Layout.fillWidth: true }
                            ActionButton { text: window.t("ui_layout.build_ui.add_recordings"); enabled: !backend.transcribing; onClicked: backend.add_files() }
                        }
                        ListView {
                            id: queueList
                            objectName: "queueList"
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true
                            model: queueModel
                            activeFocusOnTab: true
                            keyNavigationEnabled: true
                            spacing: 6
                            ScrollBar.vertical: ScrollBar {}
                            delegate: ItemDelegate {
                                id: queueRow
                                required property int index
                                required property string fileName
                                required property string source
                                required property string jobState
                                required property string stateLabel
                                required property string project
                                width: ListView.view.width
                                height: 74
                                highlighted: queueList.currentIndex === index
                                Accessible.name: fileName + ", " + stateLabel
                                onClicked: { queueList.currentIndex = index; window.queueSelection = index }
                                onDoubleClicked: backend.open_result(index)
                                background: Rectangle { radius: window.p.contrast ? 0 : 8; color: queueRow.highlighted ? window.p.blue : window.p.field; border.color: queueRow.highlighted ? window.p.blue : window.p.border }
                                contentItem: RowLayout {
                                    spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Caption { text: queueRow.fileName; color: queueRow.highlighted ? window.p.accent_text : window.p.text; font.bold: true; Layout.fillWidth: true; maximumLineCount: 1; elide: Text.ElideRight }
                                        Caption { text: queueRow.stateLabel; color: queueRow.highlighted ? window.p.accent_text : window.p.muted; font.pixelSize: 12 }
                                    }
                                    ActionButton { text: window.t("ui_layout.build_ui.open_transcript"); visible: queueRow.project.length > 0; enabled: !backend.busy; onClicked: backend.open_result(queueRow.index) }
                                    ActionButton { text: "⋯"; Accessible.name: window.t("ui_layout.build_ui.more_options"); onClicked: { window.queueSelection = queueRow.index; queueMenu.popup() } }
                                }
                            }
                        }
                    }
                    DropArea {
                        anchors.fill: parent
                        enabled: !backend.transcribing
                        onEntered: function(drag) { drag.accepted = drag.hasUrls }
                        onDropped: function(drop) {
                            if (drop.hasUrls && (drop.supportedActions & Qt.CopyAction)) {
                                backend.add_urls(drop.urls)
                                drop.accept(Qt.CopyAction)
                            }
                        }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: window.width < 700 ? 1 : 2
                    columnSpacing: 16
                    ColumnLayout {
                        Layout.fillWidth: true
                        Caption { text: window.t("ui_layout.build_ui.audio_language"); color: window.p.muted; font.pixelSize: 12 }
                        ChoiceField { objectName: "languageChoice"; Layout.fillWidth: true; model: backend.languages; textRole: "label"; valueRole: "value"; selectedValue: backend.settings.language; enabled: !backend.transcribing; onActivated: backend.option("language", currentValue); Accessible.name: window.t("ui_layout.build_ui.audio_language") }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Caption { text: window.t("studio.quality"); color: window.p.muted; font.pixelSize: 12 }
                        ChoiceField { objectName: "qualityChoice"; Layout.fillWidth: true; model: backend.qualities; textRole: "label"; valueRole: "value"; selectedValue: backend.settings.model; enabled: !backend.transcribing; onActivated: backend.option("model", currentValue); Accessible.name: window.t("studio.quality") }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: window.t("qml.first_use"); color: window.p.muted; font.pixelSize: 12; Layout.fillWidth: true; visible: !backend.busy }
                    Item { Layout.fillWidth: true; visible: backend.busy }
                    ActionButton { objectName: "startButton"; text: window.t("ui_layout.build_ui.start_transcription"); primary: true; visible: backend.queueCount > 0 && !backend.transcribing; enabled: !backend.busy; onClicked: backend.start() }
                    ActionButton { objectName: "stopButton"; text: window.t("ui_layout.build_ui.stop"); visible: backend.busy; onClicked: backend.cancel() }
                }
            }

            ColumnLayout {
                spacing: 10
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Caption { text: backend.projectName; font.pixelSize: 19; font.bold: true; width: Math.min(300, window.width-50); elide: Text.ElideRight; maximumLineCount: 1; height: 42; verticalAlignment: Text.AlignVCenter }
                    ActionButton { objectName: "saveButton"; text: window.t("exports.save_project") + (backend.dirty ? " *" : ""); primary: true; enabled: !backend.busy; onClicked: backend.save() }
                    ActionButton { text: window.t("exports.options"); enabled: !backend.busy && !backend.dirty && backend.exportSources.length > 0; onClicked: exportDialog.open() }
                    ActionButton { text: window.t("qml.editor_tools"); onClicked: editorTools.open() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    EntryField { id: searchField; objectName: "searchField"; Layout.fillWidth: true; placeholderText: window.t("accessibility.search"); onAccepted: backend.search(text, false); Accessible.name: placeholderText }
                    ActionButton { text: "‹"; Accessible.name: window.t("search.previous"); onClicked: backend.search(searchField.text,true) }
                    ActionButton { text: "›"; Accessible.name: window.t("search.next"); onClicked: backend.search(searchField.text,false) }
                    Caption { text: backend.searchCount; Layout.minimumWidth: 50 }
                }
                SplitView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    orientation: window.width < 850 ? Qt.Vertical : Qt.Horizontal
                    Panel {
                        SplitView.preferredWidth: 330
                        SplitView.preferredHeight: 150
                        SplitView.minimumHeight: 70
                        SplitView.minimumWidth: 180
                        ListView {
                            id: segmentList
                            objectName: "segmentList"
                            anchors.fill: parent; anchors.margins: 8
                            model: segmentModel
                            currentIndex: backend.selectedIndex
                            clip: true
                            activeFocusOnTab: true
                            keyNavigationEnabled: true
                            spacing: 4
                            ScrollBar.vertical: ScrollBar {}
                            onCurrentIndexChanged: if (currentIndex >= 0 && currentIndex !== backend.selectedIndex) backend.select(currentIndex)
                            delegate: ItemDelegate {
                                id: segmentRow
                                required property int index
                                required property string bodyText
                                required property real start
                                required property real end
                                required property string speaker
                                width: ListView.view.width
                                height: 80
                                highlighted: segmentList.currentIndex === index
                                onClicked: backend.select(index)
                                Accessible.name: start.toFixed(2) + " " + speaker + " " + bodyText
                                background: Rectangle { radius: window.p.contrast ? 0 : 6; color: segmentRow.highlighted ? window.p.blue : window.p.card }
                                contentItem: ColumnLayout {
                                    Caption { text: segmentRow.start.toFixed(2) + " – " + segmentRow.end.toFixed(2) + (segmentRow.speaker ? " · " + segmentRow.speaker : ""); color: segmentRow.highlighted ? window.p.accent_text : window.p.muted; font.pixelSize: 11; Layout.fillWidth: true; maximumLineCount: 1; elide: Text.ElideRight }
                                    Caption { text: segmentRow.bodyText; color: segmentRow.highlighted ? window.p.accent_text : window.p.text; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                    Panel {
                        SplitView.fillWidth: true; SplitView.fillHeight: true
                        SplitView.minimumWidth: 220; SplitView.minimumHeight: 90
                        ScrollView {
                            anchors.fill: parent; anchors.margins: 8
                            TextArea {
                                id: editor
                                objectName: "transcriptEditor"
                                readOnly: !backend.editable
                                textFormat: TextEdit.PlainText
                                wrapMode: TextEdit.Wrap
                                persistentSelection: true
                                selectByMouse: true
                                color: window.p.text
                                selectionColor: window.p.blue
                                selectedTextColor: window.p.accent_text
                                font.family: "Segoe UI"; font.pixelSize: 17
                                placeholderText: window.t("qml.select_segment")
                                Accessible.name: window.t("qml.transcript_text")
                                onTextEdited: backend.edit_active(text)
                                Keys.onPressed: function(event) {
                                    if (event.modifiers & Qt.ControlModifier) {
                                        if (event.key === Qt.Key_Z) { backend.undo(); event.accepted = true }
                                        if (event.key === Qt.Key_Y) { backend.redo(); event.accepted = true }
                                    }
                                }
                                background: Rectangle { color: window.p.field; radius: window.p.contrast ? 0 : 6 }
                            }
                        }
                    }
                }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    ActionButton { text: window.t("editor.undo"); enabled: backend.editable; onClicked: backend.undo() }
                    ActionButton { text: window.t("editor.redo"); enabled: backend.editable; onClicked: backend.redo() }
                    ActionButton { text: window.t("editor.init.segment"); enabled: backend.audioReady; onClicked: backend.play_segment() }
                    ActionButton { text: backend.playing ? window.t("editor.init.pause") : window.t("editor.init.resume"); enabled: backend.audioReady; onClicked: backend.playing ? backend.pause() : backend.play() }
                    ActionButton { text: window.t("playback.settings"); onClicked: audioDialog.open() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Slider { objectName: "seekSlider"; Layout.fillWidth: true; from: 0; to: Math.max(1,backend.duration); value: backend.position; enabled: backend.audioReady; onMoved: backend.seek(value); Accessible.name: window.t("qml.audio_position") }
                    Caption { text: backend.position.toFixed(1) + " / " + backend.duration.toFixed(1) + " s"; font.pixelSize: 12 }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: backend.exportState; color: window.p.muted; Layout.fillWidth: true; font.pixelSize: 12; maximumLineCount: 2; elide: Text.ElideRight }
                    ActionButton { text: window.t("editor.init.retry_export"); enabled: !backend.busy; onClicked: backend.retry_export() }
                    ActionButton { text: window.t("editor.init.open_export"); onClicked: backend.open_export() }
                }
            }

            ColumnLayout {
                Caption { text: window.t("ui_layout.labels.models"); font.pixelSize: 24; font.bold: true }
                Caption { text: window.t("qml.models_optional"); color: window.p.muted; Layout.fillWidth: true }
                ListView {
                    id: modelsList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    model: modelInventory
                    clip: true; spacing: 6
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        id: modelRow
                        required property int index
                        required property string modelId
                        required property string availability
                        required property real size
                        width: ListView.view.width; height: 70
                        highlighted: modelsList.currentIndex === index
                        onClicked: modelsList.currentIndex = index
                        contentItem: ColumnLayout {
                            Caption { text: modelRow.modelId; font.bold: true; Layout.fillWidth: true; maximumLineCount: 1; elide: Text.ElideRight }
                            Caption { text: window.t("integrity.state."+modelRow.availability) + " · " + (modelRow.size/1048576).toFixed(1) + " MB"; font.pixelSize: 12; color: window.p.muted }
                        }
                        background: Rectangle { radius: window.p.contrast ? 0 : 8; color: modelRow.highlighted ? window.p.field : window.p.card; border.color: modelRow.highlighted ? window.p.blue : window.p.border }
                    }
                }
                Flow {
                    Layout.fillWidth: true; spacing: 8
                    ActionButton { text: window.t("model_dialog.init.download"); enabled: !backend.busy && modelsList.currentIndex >= 0; onClicked: backend.model_action("download", backend.model_id(modelsList.currentIndex)) }
                    ActionButton { text: window.t("integrity.verify"); enabled: !backend.busy && modelsList.currentIndex >= 0; onClicked: backend.model_action("verify",backend.model_id(modelsList.currentIndex)) }
                    ActionButton { text: window.t("model_dialog.init.remove"); enabled: !backend.busy && modelsList.currentIndex >= 0; onClicked: backend.model_action("remove",backend.model_id(modelsList.currentIndex)) }
                    ActionButton { text: window.t("model_dialog.init.refresh"); enabled: !backend.busy; onClicked: backend.refresh_models() }
                    ActionButton { text: window.t("ui_layout.build_ui.stop"); visible: backend.busy; onClicked: backend.cancel() }
                }
            }

            ScrollView {
                clip: true; contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Caption { text: window.t("studio.advanced"); font.pixelSize: 24; font.bold: true }
                    Caption { text: window.t("ui_layout.build_ui.device") }
                    ChoiceField { Layout.fillWidth: true; model: backend.devices; textRole: "label"; valueRole: "value"; selectedValue: backend.settings.device; enabled: !backend.transcribing; onActivated: backend.option("device",currentValue) }
                    CheckBox { text: window.t("ui_layout.build_ui.offline_only"); checked: backend.settings.offline; enabled: !backend.transcribing; onToggled: backend.option("offline",checked) }
                    CheckBox { text: window.t("ui_layout.build_ui.play_audio_automatically_when_selecting_an_editor_segment"); checked: backend.settings.autoplay; onToggled: backend.option("autoplay",checked) }
                    Caption { text: window.t("ui_layout.build_ui.save_to") }
                    RowLayout {
                        Layout.fillWidth: true
                        EntryField { text: backend.settings.output; readOnly: true; Layout.fillWidth: true }
                        ActionButton { text: window.t("ui_layout.build_ui.browse"); enabled: !backend.transcribing; onClicked: backend.choose_output() }
                    }
                    Caption { text: window.t("settings.ui_language") }
                    ChoiceField { model: ["Slovenčina", "English"]; currentIndex: backend.settings.ui_language === "sk" ? 0 : 1; onActivated: backend.option("ui_language",currentIndex === 0 ? "sk" : "en") }
                    Caption { text: window.t("settings.restart"); color: window.p.muted; Layout.fillWidth: true }
                    ActionButton { text: window.t("qml.change_theme"); onClicked: backend.toggle_theme() }
                    Caption { text: window.t("qml.shortcuts"); color: window.p.muted; Layout.fillWidth: true }
                }
            }

            ColumnLayout {
                Caption { text: window.t("data.title"); font.pixelSize: 24; font.bold: true }
                RowLayout {
                    ActionButton { text: window.t("data.refresh"); enabled: !backend.busy; onClicked: { diagnosticText.showPreview = false; backend.inspect_data() } }
                    ActionButton { text: window.t("data.preview"); enabled: backend.diagnostic.length > 0 && !backend.busy; onClicked: { diagnosticText.showPreview = true; backend.preview_diagnostic() } }
                    ActionButton { text: window.t("data.save"); primary: true; enabled: backend.diagnosticPreviewed && !backend.busy; onClicked: backend.save_diagnostic() }
                }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ReadOnlyText { id: diagnosticText; property bool showPreview: false; text: showPreview ? backend.diagnosticPreview : backend.dataOverview; Accessible.name: window.t("data.preview") }
                }
            }

            ColumnLayout {
                Caption { text: window.t("ui_layout.build_ui.activity_log"); font.pixelSize: 24; font.bold: true }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; ReadOnlyText { text: backend.logs; Accessible.name: window.t("ui_layout.build_ui.activity_log") } }
                ActionButton { text: window.t("ui_layout.build_ui.clear_preview_and_messages"); onClicked: backend.clear_log() }
            }
        }

        Panel {
            Layout.fillWidth: true
            implicitHeight: progressBox.implicitHeight+20
            visible: backend.transcribing
            ColumnLayout {
                id: progressBox
                anchors.fill: parent; anchors.margins: 10
                Caption { text: backend.status; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight }
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: window.t("ui_layout.build_ui.recording"); font.pixelSize: 12 }
                    ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: backend.progress; Accessible.name: window.t("ui_layout.build_ui.recording") }
                    Caption { text: backend.progress.toFixed(0)+" %"; font.pixelSize: 12 }
                    Caption { text: window.t("ui_layout.build_ui.batch"); font.pixelSize: 12 }
                    ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: backend.batchProgress; Accessible.name: window.t("ui_layout.build_ui.batch") }
                }
                Caption { text: backend.timing; font.pixelSize: 11; color: window.p.muted; Layout.fillWidth: true }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { running: backend.busy && !backend.transcribing; visible: running; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
            Caption { text: backend.transcribing ? "" : backend.status; color: window.p.muted; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight; font.pixelSize: 12 }
            ActionButton { text: window.t("error.details"); visible: backend.issue.length > 0; onClicked: errorDialog.open() }
        }
    }

    footer: Label { padding: 8; color: window.p.muted; font.pixelSize: 10; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignRight; text: backend.version + " · Created by Daniel Návojský (ndxnraw) using Codex | 2026" }

    Menu {
        id: queueMenu
        MenuItem { text: window.t("ui_layout.build_ui.open_transcript"); enabled: !backend.busy; onTriggered: backend.open_result(window.queueSelection) }
        MenuItem { text: window.t("prepis.update_selection.resume"); enabled: !backend.busy; onTriggered: backend.retry(window.queueSelection,false) }
        MenuItem { text: window.t("ui_layout.build_ui.new_transcription_from_start"); enabled: !backend.busy; onTriggered: backend.retry(window.queueSelection,true) }
        MenuSeparator {}
        MenuItem { text: window.t("ui_layout.build_ui.move_up"); enabled: !backend.transcribing; onTriggered: backend.move(window.queueSelection,-1) }
        MenuItem { text: window.t("ui_layout.build_ui.move_down"); enabled: !backend.transcribing; onTriggered: backend.move(window.queueSelection,1) }
        MenuItem { text: window.t("workspace.remove_from_queue"); enabled: !backend.transcribing; onTriggered: backend.remove(window.queueSelection) }
        MenuItem { text: window.t("ui_layout.build_ui.details"); onTriggered: { queueInfo.text = backend.queue_info(window.queueSelection); queueInfoDialog.open() } }
    }

    Dialog {
        id: questionDialog
        property string kind: ""
        property string questionText: ""
        anchors.centerIn: parent
        width: Math.min(window.width-32,600)
        modal: true
        title: window.t("qml.confirm")
        standardButtons: Dialog.Yes | Dialog.No
        closePolicy: Popup.NoAutoClose
        contentItem: Caption { text: questionDialog.questionText }
        onAccepted: backend.answer(kind,true)
        onRejected: backend.answer(kind,false)
    }
    Dialog {
        id: dirtyDialog
        anchors.centerIn: parent
        width: Math.min(window.width-32,600)
        modal: true
        title: window.t("qml.unsaved")
        closePolicy: Popup.NoAutoClose
        contentItem: ColumnLayout {
            Caption { text: window.t("qml.unsaved_question"); Layout.fillWidth: true }
            Flow {
                Layout.fillWidth: true; spacing: 8
                ActionButton { text: window.t("exports.save_project"); primary: true; onClicked: { dirtyDialog.close(); backend.resolve_dirty("save") } }
                ActionButton { text: window.t("qml.discard"); onClicked: { dirtyDialog.close(); backend.resolve_dirty("discard") } }
                ActionButton { text: window.t("qml.cancel"); onClicked: { dirtyDialog.close(); backend.resolve_dirty("cancel") } }
            }
        }
    }
    Dialog {
        id: errorDialog
        anchors.centerIn: parent
        width: Math.min(window.width-32,720)
        modal: true
        title: window.t("error.details")
        standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            Caption { text: backend.status; Layout.fillWidth: true }
            ScrollView { Layout.fillWidth: true; Layout.preferredHeight: Math.min(300,window.height-250); ReadOnlyText { text: backend.issue } }
        }
    }
    Dialog {
        id: queueInfoDialog
        anchors.centerIn: parent; width: Math.min(window.width-32,720)
        modal: true; title: window.t("ui_layout.build_ui.details"); standardButtons: Dialog.Close
        contentItem: ScrollView { implicitHeight: Math.min(320,window.height-200); ReadOnlyText { id: queueInfo } }
    }
    Dialog {
        id: aboutDialog
        anchors.centerIn: parent; width: Math.min(window.width-32,600)
        modal: true; title: window.t("about.title"); standardButtons: Dialog.Close
        contentItem: Caption { text: "ND TranskripThor · " + backend.version + "\n\nCreated by Daniel Návojský (ndxnraw) using Codex | 2026\n\n" + window.t("qml.privacy") }
    }
    Dialog {
        id: audioDialog
        anchors.centerIn: parent; width: Math.min(window.width-32,600)
        modal: true; title: window.t("playback.settings"); standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: { outputDevice.model = backend.audio_devices(); speed.currentIndex = [0.75,1,1.25,1.5].indexOf(backend.playbackRate) }
        onAccepted: backend.configure_audio([0.75,1,1.25,1.5][speed.currentIndex],outputDevice.currentIndex)
        contentItem: ColumnLayout {
            Caption { text: window.t("playback.output") }
            ChoiceField { id: outputDevice; Layout.fillWidth: true }
            Caption { text: window.t("playback.speed") }
            ChoiceField { id: speed; Layout.fillWidth: true; model: ["0.75×","1×","1.25×","1.5×"] }
            ActionButton { text: window.t("project.audio_choose"); enabled: !backend.busy; onClicked: backend.choose_audio() }
        }
    }
    Dialog {
        id: exportDialog
        anchors.centerIn: parent; width: Math.min(window.width-32,680)
        modal: true; title: window.t("exports.options"); standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            let selected = []
            for (let i=0; i<formats.count; i++) if (formats.itemAt(i).checked) selected.push(formats.itemAt(i).text.toLowerCase())
            backend.export_files(selected,exportTimes.checked,exportSpeakers.checked,exportSource.currentValue)
        }
        contentItem: ColumnLayout {
            Caption { text: window.t("exports.source") }
            ChoiceField { id: exportSource; Layout.fillWidth: true; model: backend.exportSources; textRole: "label"; valueRole: "value" }
            Flow { Layout.fillWidth: true; Repeater { id: formats; model: ["TXT","SRT","VTT","DOCX","JSON"]; CheckBox { required property string modelData; text: modelData; checked: modelData === "TXT" || modelData === "SRT" } } }
            CheckBox { id: exportTimes; text: window.t("exports.times") }
            CheckBox { id: exportSpeakers; text: window.t("exports.speakers") }
            Caption { text: window.t("exports.help"); Layout.fillWidth: true; color: window.p.muted }
        }
    }
    Dialog {
        id: editorTools
        anchors.centerIn: parent; width: Math.min(window.width-32,720)
        height: Math.min(window.height-48,680)
        modal: true; title: window.t("qml.editor_tools"); standardButtons: Dialog.Close
        onOpened: {
            speakerName.text = backend.activeSegment.speaker || ""
            startTime.text = backend.activeSegment.start.toFixed(3)
            endTime.text = backend.activeSegment.end.toFixed(3)
            splitTime.text = ((backend.activeSegment.start+backend.activeSegment.end)/2).toFixed(3)
        }
        contentItem: ScrollView {
            clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 10
                Caption { text: window.t("editor.init.segment_speaker"); font.bold: true }
                EntryField { id: speakerName; Layout.fillWidth: true; Accessible.name: window.t("editor.init.segment_speaker") }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    ActionButton { text: window.t("qml.apply_speaker"); onClicked: backend.speaker(speakerName.text,false) }
                    ActionButton { text: window.t("qml.rename_voice"); onClicked: backend.speaker(speakerName.text,true) }
                    ActionButton { text: window.t("editor.init.group_similar_voices"); enabled: backend.audioReady && !backend.busy; onClicked: backend.group_voices() }
                }
                Caption { text: window.t("segments.times"); font.bold: true }
                RowLayout {
                    EntryField { id: startTime; Layout.fillWidth: true; placeholderText: window.t("segments.start"); validator: DoubleValidator { bottom: 0 } }
                    EntryField { id: endTime; Layout.fillWidth: true; placeholderText: window.t("segments.end"); validator: DoubleValidator { bottom: 0 } }
                    ActionButton { text: window.t("qml.apply"); enabled: !backend.busy; onClicked: backend.structure("times",0,Number(startTime.text.replace(",",".")),Number(endTime.text.replace(",","."))) }
                }
                Caption { text: window.t("segments.split_time") }
                EntryField { id: splitTime; Layout.fillWidth: true; validator: DoubleValidator { bottom: 0 } }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    ActionButton { text: window.t("segments.split"); enabled: !backend.busy; onClicked: backend.structure("split",editor.cursorPosition,Number(splitTime.text.replace(",",".")),0) }
                    ActionButton { text: window.t("segments.merge"); enabled: !backend.busy; onClicked: backend.structure("merge",0,0,0) }
                }
                Caption { text: window.t("editor.init.segment_and_subtitles"); font.bold: true }
                GridLayout {
                    Layout.fillWidth: true; columns: 2
                    Caption { text: window.t("editor.labels.chars_line") }
                    SpinBox { id: subtitleChars; from: 10; to: 120; value: backend.subtitleSettings.characters }
                    Caption { text: window.t("editor.labels.lines") }
                    SpinBox { id: subtitleLines; from: 1; to: 4; value: backend.subtitleSettings.lines }
                    Caption { text: window.t("editor.init.min_seconds") }
                    EntryField { id: subtitleMinimum; text: String(backend.subtitleSettings.minimum); Layout.fillWidth: true }
                    Caption { text: window.t("editor.init.max_seconds") }
                    EntryField { id: subtitleMaximum; text: String(backend.subtitleSettings.maximum); Layout.fillWidth: true }
                }
                ActionButton { text: window.t("qml.apply"); onClicked: backend.subtitles(subtitleChars.value,subtitleLines.value,Number(subtitleMinimum.text.replace(",",".")),Number(subtitleMaximum.text.replace(",","."))) }
            }
        }
    }

    Shortcut { sequence: "Ctrl+O"; onActivated: backend.choose_project() }
    Shortcut { sequence: "Ctrl+S"; enabled: backend.view === "editor"; onActivated: backend.save() }
    Shortcut { sequence: "Ctrl+F"; enabled: backend.view === "editor"; onActivated: { searchField.forceActiveFocus(); searchField.selectAll() } }
    Shortcut { sequence: "F3"; enabled: backend.view === "editor"; onActivated: backend.search(searchField.text,false) }
    Shortcut { sequence: "Shift+F3"; enabled: backend.view === "editor"; onActivated: backend.search(searchField.text,true) }
    Shortcut { sequence: "Alt+Home"; onActivated: backend.show("home") }
    Connections {
        target: backend
        function onSelectionChanged() {
            editor.text = backend.activeSegment.text || ""
            if (backend.selectedIndex >= 0) segmentList.positionViewAtIndex(backend.selectedIndex,ListView.Contain)
            if (backend.selectionEnd > backend.selectionStart) {
                editor.forceActiveFocus()
                editor.select(backend.selectionStart,backend.selectionEnd)
            }
        }
        function onQuestionRequested(kind,text) { questionDialog.kind = kind; questionDialog.questionText = text; questionDialog.open() }
        function onDirtyRequested() { dirtyDialog.open() }
        function onCloseReady() { window.forceClose = true; window.close() }
        function onIssueRaised(summary,detail) { /* The persistent Details action opens the read-only diagnostic. */ }
    }
}
