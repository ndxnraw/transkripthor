import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "prototypeWindow"
    visible: true
    width: 1000; height: 720
    minimumWidth: 480; minimumHeight: 420
    title: "ND TranskripThor — QML Testing"
    property bool dark: true
    Material.theme: dark ? Material.Dark : Material.Light
    Material.accent: Material.Blue
    onClosing: function(close) { close.accepted = backend.can_close() }
    Shortcut { sequence: "Ctrl+S"; onActivated: backend.save() }
    header: ToolBar {
        RowLayout {
            anchors.fill: parent; anchors.margins: 8
            Image { source: "../assets/transkripthor.png"; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
            Label { text: "ND TranskripThor · Testing"; Layout.fillWidth: true; elide: Text.ElideRight }
            Switch { objectName: "themeSwitch"; text: "Tmavý"; checked: window.dark; onToggled: window.dark = checked; Accessible.name: "Tmavý vzhľad" }
        }
    }
    footer: ColumnLayout {
        width: parent.width; spacing: 2
        RowLayout {
            Layout.fillWidth: true
            Button { objectName: "startButton"; text: "Spustiť na CPU"; enabled: !backend.busy; onClicked: backend.start(language.currentText,model.currentText,offline.checked) }
            Button { text: "Zastaviť"; enabled: backend.busy; onClicked: backend.cancel(); Accessible.name: text }
            Item { Layout.fillWidth: true }
            Button { objectName: "saveButton"; text: backend.dirty ? "Uložiť *" : "Uložiť"; enabled: backend.dirty && !backend.busy; onClicked: backend.save(); Accessible.name: "Uložiť pracovnú kópiu projektu" }
        }
        ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: backend.progress; Accessible.name: "Priebeh aktuálnej nahrávky" }
        Label { text: backend.status; Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; Accessible.name: text }
        Label { text: "Created by Daniel Návojský (ndxnraw) using Codex | 2026"; Layout.fillWidth: true; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignRight; font.pixelSize: 11 }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12
        TabBar {
            id: tabs; objectName: "workspaceTabs"; Layout.fillWidth: true
            TabButton { text: "Nahrávky" }
            TabButton { text: "Editor" }
        }
        StackLayout {
            currentIndex: tabs.currentIndex; Layout.fillWidth: true; Layout.fillHeight: true
            ScrollView {
              id: queueScroll
              objectName: "queueScroll"
              clip: true
              implicitWidth: 0
              implicitHeight: 0
              contentWidth: availableWidth
              contentHeight: Math.max(400,height)
              ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                id: queueColumn
                width: queueScroll.availableWidth
                height: queueScroll.contentHeight
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    Button { text: "Pridať nahrávky"; enabled: !backend.busy; onClicked: backend.add_files() }
                    Button { text: "Odobrať z fronty"; enabled: !backend.busy; onClicked: backend.remove(queueList.currentIndex) }
                    Button { text: "Otvoriť výsledok"; enabled: !backend.busy && !backend.dirty; onClicked: { backend.open_result(queueList.currentIndex); tabs.currentIndex=1 } }
                }
                ListView {
                    id: queueList; objectName: "queueList"; Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true; model: queueModel; activeFocusOnTab: true; keyNavigationEnabled: true
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        required property int index; required property string source; required property string jobState
                        width: ListView.view.width; text: source + " — " + jobState; highlighted: queueList.currentIndex===index
                        onClicked: queueList.currentIndex=index
                        Accessible.name: text
                    }
                }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    ComboBox { id: language; model: ["sk","cs","en","hu","cs-sk"]; Accessible.name: "Jazyk nahrávky"; enabled: !backend.busy }
                    ComboBox { id: model; model: ["tiny","small","medium","large-v3","kinit/whisper-large-v3-sk"]; Accessible.name: "Model"; enabled: !backend.busy }
                    CheckBox { id: offline; text: "Iba offline"; checked: true; enabled: !backend.busy }
                }
              }
            }
            ColumnLayout {
                Button { text: "Otvoriť kópiu projektu…"; enabled: !backend.busy && !backend.dirty; onClicked: backend.choose_project() }
                SplitView {
                    Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Vertical
                    ListView {
                        id: segments; objectName: "segmentList"; SplitView.fillHeight: true; SplitView.minimumHeight: 70
                        clip: true; model: segmentModel; activeFocusOnTab: true; keyNavigationEnabled: true
                        ScrollBar.vertical: ScrollBar {}
                        onCurrentIndexChanged: if(currentIndex>=0) editor.text=backendText(currentIndex)
                        function backendText(i) { return backend.segment_text(i) }
                        delegate: ItemDelegate {
                            required property int index; required property string bodyText; required property real start; required property real end
                            width: ListView.view.width; highlighted: segments.currentIndex===index
                            contentItem: Label { text: start.toFixed(2)+" – "+end.toFixed(2)+"  "+parent.bodyText; elide: Text.ElideRight }
                            onClicked: { segments.currentIndex=index; editor.text=bodyText }
                            Accessible.name: start.toFixed(2)+" sekúnd: "+bodyText
                        }
                    }
                    ScrollView {
                        SplitView.preferredHeight: 140; SplitView.minimumHeight: 60
                        TextArea { id: editor; objectName: "transcriptEditor"; wrapMode: TextEdit.Wrap; enabled: !backend.busy; selectByMouse: true
                            Accessible.name: "Text vybraného úseku"; placeholderText: "Vyberte úsek prepisu"
                            onTextChanged: backend.edit(segments.currentIndex,text)
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button { text: "Prehrať"; enabled: backend.duration>0 && !backend.busy; onClicked: backend.play() }
                    Button { text: "Pauza"; onClicked: backend.pause() }
                    Slider { objectName: "seekSlider"; Layout.fillWidth: true; from: 0; to: Math.max(1,backend.duration); value: backend.position; enabled: backend.duration>0 && !backend.busy; onMoved: backend.seek(value); Accessible.name: "Pozícia zvuku v sekundách" }
                    Label { text: backend.position.toFixed(1)+" s" }
                }
            }
        }
    }
}
