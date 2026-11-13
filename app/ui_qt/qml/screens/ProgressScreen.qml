import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas
    property var metrics: assessmentController.historyAnalytics

    function durationLabel(milliseconds) {
        var minutes = Math.floor(milliseconds / 60000)
        if (milliseconds < 1000) return "<1 sec"
        if (milliseconds < 60000) return Math.floor(milliseconds / 1000) + " sec"
        var hours = Math.floor(minutes / 60)
        minutes = minutes % 60
        if (hours > 0) return hours + "h " + minutes + "m"
        return minutes + "m"
    }

    Row {
        anchors.fill: parent

        NavRail {
            width: Metrics.navRailWidth
            height: parent.height
            currentTab: "progress"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home")
                else if (tab === "library") appController.navigate("subjects")
                else if (tab === "practice") appController.navigate("content")
                else if (tab === "progress") appController.navigate("progress")
                else if (tab === "history") appController.navigate("history")
                else if (tab === "settings") appController.navigate("settings")
            }
        }

        Column {
            width: parent.width - Metrics.navRailWidth
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Progress & Analytics"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
            }

            Flickable {
                id: content
                objectName: "progressAnalyticsFlickable"
                width: parent.width
                height: parent.height - Metrics.headerHeight
                contentWidth: width
                contentHeight: body.implicitHeight + Spacing.md * 2
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: body
                    width: parent.width - Spacing.md * 2
                    x: Spacing.md
                    y: Spacing.sm
                    spacing: Spacing.sm

                    AppCard {
                        width: parent.width
                        height: 94

                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: Spacing.md

                            Column {
                                width: parent.width - viewHistory.width - Spacing.md
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 5

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        width: parent.width - windowPicker.width - parent.spacing
                                        text: metrics.attempts + " of last " + assessmentController.analyticsWindow + " assessments"
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.sectionTitle
                                        font.bold: true
                                        font.family: Typography.familyEditorial
                                        elide: Text.ElideRight
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    ComboBox {
                                        id: windowPicker
                                        width: 116
                                        height: 32
                                        model: [5, 10, 20]
                                        currentIndex: [5, 10, 20].indexOf(assessmentController.analyticsWindow)
                                        displayText: "Last " + currentValue
                                        font.pixelSize: Typography.caption
                                        onActivated: assessmentController.setAnalyticsWindow(Number(currentValue))
                                    }
                                }

                                Text {
                                    text: "Accuracy " + (metrics.accuracyPercent < 0 ? "Not enough answers yet" : metrics.accuracyPercent + "%")
                                          + "   •   " + metrics.correct + " correct   •   " + metrics.wrong + " incorrect   •   " + metrics.skipped + " skipped"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.family
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: "Practice " + root.durationLabel(metrics.practiceTimeMs)
                                          + "   •   " + metrics.deviceAttempts + " on Pi   •   " + metrics.webAttempts + " on web"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.family
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }

                            SecondaryButton {
                                id: viewHistory
                                anchors.verticalCenter: parent.verticalCenter
                                text: "History"
                                preferredHeight: Metrics.touchNormal
                                onClicked: appController.navigate("history")
                            }
                        }
                    }

                    AppCard {
                        width: parent.width
                        height: 152

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: 6

                            Text {
                                text: "Accuracy over recent assessments"
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.bold: true
                                font.family: Typography.familyEditorial
                            }

                            Item {
                                width: parent.width
                                height: 92

                                Text {
                                    anchors.centerIn: parent
                                    visible: metrics.trends.length === 0
                                    text: "Complete an assessment to start a trend."
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                }

                                Row {
                                    anchors.fill: parent
                                    spacing: 8
                                    visible: metrics.trends.length > 0

                                    Repeater {
                                        model: metrics.trends

                                        delegate: Column {
                                            width: (parent.width - 8 * (metrics.trends.length - 1)) / Math.max(1, metrics.trends.length)
                                            height: parent.height
                                            spacing: 3

                                            Item {
                                                width: parent.width
                                            height: 58

                                                Rectangle {
                                                    anchors.bottom: parent.bottom
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    width: Math.min(28, parent.width - 4)
                                                    height: modelData.accuracyPercent < 0 ? 2 : Math.max(4, 54 * modelData.accuracyPercent / 100)
                                                    radius: 4
                                                    color: modelData.accuracyPercent < 0 ? Theme.border : Theme.forest
                                                }
                                            }

                                            Text {
                                                width: parent.width
                                                horizontalAlignment: Text.AlignHCenter
                                                text: modelData.accuracyPercent < 0 ? "–" : modelData.accuracyPercent + "%"
                                                color: Theme.deepInk
                                                font.pixelSize: 10
                                                font.bold: true
                                            }

                                            Text {
                                                width: parent.width
                                                horizontalAlignment: Text.AlignHCenter
                                                text: modelData.label
                                                color: Theme.mutedInk
                                                font.pixelSize: 8
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    AppCard {
                        width: parent.width
                        height: 184

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: 4

                            Text {
                                text: "Confidence check"
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.bold: true
                                font.family: Typography.familyEditorial
                            }

                            Text {
                                text: "See how your confidence matched your answers."
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.family
                            }

                            Repeater {
                                model: [
                                    {key: "sure", label: "Sure"},
                                    {key: "not_sure", label: "Not sure"},
                                    {key: "guessing", label: "Guessing"},
                                    {key: "unrated", label: "No confidence rating"}
                                ]

                                delegate: Row {
                                    width: parent.width
                                    height: 22
                                    spacing: 8

                                    Text {
                                        width: 120
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.label
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.family
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        width: 110
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: metrics.confidence[modelData.key].correct + " correct · " + metrics.confidence[modelData.key].wrong + " incorrect"
                                        color: Theme.mutedInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.family
                                    }

                                    Rectangle {
                                        width: parent.width - 246
                                        height: 7
                                        anchors.verticalCenter: parent.verticalCenter
                                        radius: 4
                                        color: Theme.borderLight

                                        Rectangle {
                                            width: {
                                                var total = metrics.confidence[modelData.key].correct + metrics.confidence[modelData.key].wrong
                                                return total > 0 ? parent.width * metrics.confidence[modelData.key].correct / total : 0
                                            }
                                            height: parent.height
                                            radius: parent.radius
                                            color: Theme.forest
                                        }
                                    }
                                }
                            }

                            Text {
                                objectName: "averageAnswerTimeText"
                                text: "Average answer time: " + (metrics.averageResponseTimeMs < 0 ? "–" : Math.round(metrics.averageResponseTimeMs / 1000) + " sec")
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.family
                            }
                        }
                    }
                }
            }
        }
    }
}
