import QtQuick
import QtQuick.Controls.Basic

import Modules

MenuSeparator {
    objectName: "menuSeparator"
    horizontalPadding: padding + 4    
    property bool light: false
    contentItem: Rectangle {
        implicitHeight: 1
        color: light ? Colors.panelAltBackground : Colors.textPrimary
    }
}
