import QtQuick
import QtQuick.Controls

import Modules
import Controls

WindowDialog {
    id: root
    title: "Error"
    standardButtons: DialogButtons.ok

    minimumWidth: 240

    property alias text: label.text

    content: Row {
        anchors.fill: parent
        anchors.margins: 10
        anchors.bottomMargin: 0
        spacing: 5
        padding: 5
        Image {
            id: icon
            source: "qrc:/img/error-64.png"
            anchors.verticalCenter: parent.verticalCenter
        }
        Label {
            id: label
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            width: root.width - icon.width - 30
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
