import QtQuick
import QtQuick.Controls.Basic

import Modules

MenuSeparator {
    objectName: "menuSeparator"
    horizontalPadding: padding + 4
    contentItem: Rectangle {
        implicitHeight: 1
        color: Colors.textPrimary
    }
}
