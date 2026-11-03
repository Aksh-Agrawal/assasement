import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Quick Add Questions"
        profileText: quickAddController.profileName ? quickAddController.profileName : appController.activeProfileName
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: quickAddController.cancelQuickAdd()
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md

        Row {
            anchors.fill: parent
            spacing: Spacing.md

            // Left Column: QR Code & Fallback Short Code
            AppCard {
                width: 320
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.md
                    spacing: Spacing.sm
                    anchors.horizontalCenter: parent.horizontalCenter

                    // QR Display Box
                    Rectangle {
                        width: 230
                        height: 230
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: "#FFFFFF"
                        radius: Metrics.radiusMd
                        border.color: Theme.border
                        border.width: 1

                        Image {
                            id: qrImage
                            anchors.fill: parent
                            anchors.margins: 10
                            source: quickAddController.qrSource
                            fillMode: Image.PreserveAspectFit
                            smooth: false
                            visible: quickAddController.status !== "CREATING" && quickAddController.status !== "EXPIRED" && quickAddController.qrSource.length > 0
                        }

                        // Creating state indicator
                        Column {
                            anchors.centerIn: parent
                            spacing: Spacing.sm
                            visible: quickAddController.status === "CREATING"

                            Rectangle {
                                width: 32; height: 32; radius: 16
                                color: Theme.primaryLight
                                anchors.horizontalCenter: parent.horizontalCenter
                                Image {
                                    anchors.centerIn: parent
                                    width: 18; height: 18
                                    source: Assets.refresh
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                            Text {
                                text: "Generating QR…"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // Expired state overlay
                        Column {
                            anchors.centerIn: parent
                            spacing: Spacing.sm
                            visible: quickAddController.status === "EXPIRED"

                            Text {
                                text: "QR Expired"
                                color: Theme.warning
                                font.pixelSize: Typography.body
                                font.bold: true
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: "Tap button to renew"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }

                    // Fallback Code Container
                    Rectangle {
                        width: parent.width
                        height: 78
                        radius: Metrics.radiusSm
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 2

                            Text {
                                text: "Or enter code on phone:"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }

                            Text {
                                text: quickAddController.shortCode ? quickAddController.shortCode : "--------"
                                color: Theme.forest
                                font.pixelSize: 22
                                font.bold: true
                                font.letterSpacing: 2
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }

                            Text {
                                text: "at web/quick-add"
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }

                    // Remaining time pill
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 6
                        visible: quickAddController.status !== "READY" && quickAddController.status !== "EXPIRED" && quickAddController.status !== "FAILED"

                        Image {
                            width: 14; height: 14
                            anchors.verticalCenter: parent.verticalCenter
                            source: Assets.history
                            fillMode: Image.PreserveAspectFit
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Expires in: " + quickAddController.remainingTime
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }
                }
            }

            // Right Column: Instructions, Status & Actions
            AppCard {
                width: parent.width - 320 - Spacing.md
                height: parent.height

                Column {
                    anchors.fill: parent
                    anchors.margins: Spacing.lg
                    spacing: Spacing.md

                    // Heading
                    Column {
                        spacing: 4
                        Text {
                            text: "Add Questions From Your Phone"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.title
                            font.family: Typography.fontSerif
                            font.bold: true
                        }
                        Text {
                            text: "Scan the QR code with your phone camera. No laptop or sign-in needed."
                            color: Theme.textSecondary
                            font.pixelSize: Typography.body
                            font.family: Typography.fontFamily
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    // Status Indicator Box
                    Rectangle {
                        width: parent.width
                        height: 52
                        radius: Metrics.radiusSm
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: Spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Spacing.md

                            StatusBadge {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    switch (quickAddController.status) {
                                        case "CREATING": return "Preparing";
                                        case "WAITING_FOR_PHONE": return "Waiting for phone";
                                        case "PHONE_CONNECTED": return "Phone connected";
                                        case "UPLOADING": return "Uploading";
                                        case "PROCESSING": return "Processing";
                                        case "NEEDS_REVIEW": return "Needs Review";
                                        case "SYNCING_TO_DEVICE": return "Syncing";
                                        case "READY": return "Ready to practice";
                                        case "EXPIRED": return "Expired";
                                        case "FAILED": return "Failed";
                                        default: return "Pending";
                                    }
                                }
                                statusType: {
                                    switch (quickAddController.status) {
                                        case "READY": return "success";
                                        case "PHONE_CONNECTED":
                                        case "UPLOADING":
                                        case "PROCESSING":
                                        case "SYNCING_TO_DEVICE": return "syncing";
                                        case "NEEDS_REVIEW":
                                        case "EXPIRED": return "warning";
                                        case "FAILED": return "error";
                                        default: return "neutral";
                                    }
                                }
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: quickAddController.statusText
                                color: Theme.textPrimary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                elide: Text.ElideRight
                                width: 220
                            }
                        }
                    }

                    // Content State Views:
                    // 1. Success / Ready State
                    Rectangle {
                        width: parent.width
                        height: 110
                        radius: Metrics.radiusSm
                        color: Theme.surfaceSelected
                        border.color: Theme.sage
                        border.width: 1
                        visible: quickAddController.status === "READY"

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: 4

                            Row {
                                spacing: Spacing.sm
                                Rectangle {
                                    width: 28; height: 28; radius: 14
                                    color: Theme.forest
                                    anchors.verticalCenter: parent.verticalCenter
                                    Image {
                                        anchors.centerIn: parent
                                        width: 16; height: 16
                                        source: Assets.check
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Successfully Installed!"
                                    color: Theme.forest
                                    font.bold: true
                                    font.pixelSize: Typography.body
                                    font.family: Typography.fontFamily
                                }
                            }

                            Text {
                                text: quickAddController.packTitle ? quickAddController.packTitle : "Mobile Question Pack"
                                color: Theme.textPrimary
                                font.bold: true
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: quickAddController.questionCount + " questions added to Practice"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                            }
                        }
                    }

                    // 2. Normal Instructional Steps (when not ready or failed)
                    Column {
                        width: parent.width
                        spacing: Spacing.sm
                        visible: quickAddController.status !== "READY" && quickAddController.status !== "FAILED" && quickAddController.status !== "EXPIRED"

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "1"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Scan QR code with your phone camera"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "2"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Upload PDF or type questions directly"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "3"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Confirm and practice right here on Pi"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }
                    }

                    // Spacer
                    Item {
                        width: parent.width
                        height: 1
                        anchors.bottom: buttonRow.top
                    }

                    // Bottom Buttons
                    Row {
                        id: buttonRow
                        spacing: Spacing.md
                        anchors.bottom: parent.bottom
                        anchors.right: parent.right

                        // Ready actions
                        PrimaryButton {
                            visible: quickAddController.status === "READY"
                            text: "Start Practice"
                            iconSource: Assets.practice
                            onClicked: quickAddController.practiceNow()
                        }

                        SecondaryButton {
                            visible: quickAddController.status === "READY"
                            text: "Done"
                            onClicked: appController.navigate("content")
                        }

                        // Expired / Failed actions
                        PrimaryButton {
                            visible: quickAddController.status === "EXPIRED" || quickAddController.status === "FAILED"
                            text: "Generate New QR"
                            iconSource: Assets.refresh
                            onClicked: quickAddController.retryQuickAdd()
                        }

                        // Cancel action (when not ready)
                        SecondaryButton {
                            visible: quickAddController.status !== "READY"
                            text: "Cancel"
                            onClicked: quickAddController.cancelQuickAdd()
                        }
                    }
                }
            }
        }
    }
}
