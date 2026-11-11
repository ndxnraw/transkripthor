import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    property bool danger: false
    property var tones: backend.colors
    padding: 12
    leftPadding: 18
    rightPadding: 18
    implicitHeight: 42
    Accessible.name: text
    contentItem: Text {
        text: control.text
        font.family: "Segoe UI"
        font.pixelSize: 14
        font.bold: control.primary
        color: control.primary ? control.tones.accent_text : control.tones.text
        opacity: control.enabled ? 1 : 0.5
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: control.tones.contrast ? 0 : 8
        color: control.primary ? control.tones.blue : control.hovered ? control.tones.bg : control.tones.card
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? control.tones.blue : control.primary ? control.tones.blue : control.tones.border
        opacity: control.enabled ? 1 : 0.6
    }
}
