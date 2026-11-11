import QtQuick
import QtQuick.Controls

TextField {
    id: control
    property var tones: backend.colors
    implicitHeight: 42
    padding: 10
    color: tones.text
    placeholderTextColor: tones.muted
    selectionColor: tones.blue
    selectedTextColor: tones.accent_text
    font.family: "Segoe UI"
    font.pixelSize: 14
    background: Rectangle {
        radius: control.tones.contrast ? 0 : 7
        color: control.tones.field
        border.color: control.activeFocus ? control.tones.blue : control.tones.border
        border.width: control.activeFocus ? 2 : 1
    }
}
