import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property var tones: backend.colors
    property var selectedValue: undefined
    currentIndex: selectedValue === undefined ? 0 : count > 0 ? indexOfValue(selectedValue) : -1
    implicitHeight: 42
    padding: 10
    font.family: "Segoe UI"
    font.pixelSize: 14
    contentItem: Text {
        text: control.displayText
        font: control.font
        color: control.tones.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        rightPadding: control.indicator.width+12
    }
    background: Rectangle {
        radius: control.tones.contrast ? 0 : 7
        color: control.tones.field
        border.color: control.activeFocus ? control.tones.blue : control.tones.border
        border.width: control.activeFocus ? 2 : 1
    }
}
