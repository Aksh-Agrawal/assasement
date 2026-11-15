import QtQuick 2.15
import ".." 1.0

LibraryCard {
    property var pack: ({})
    property int progressPercent: 0
    objectName: pack.id ? "practicePack-" + pack.id : ""
    title: pack.title || ""
    context: [pack.subject, pack.chapter, pack.topic].filter(function(value) { return value; }).join(" • ")
    status: !pack.questionCount ? "" : (pack.status === "Downloading" ? "Downloading " + progressPercent + "%" : pack.status)
            + " • " + pack.questionCount + (pack.questionCount === 1 ? " question" : " questions")
    ready: !!pack.isInstalled
    actionText: pack.isInstalled ? "Practice" : pack.isDownloading ? "" : pack.retry ? "Retry" : "Download"
    enabled: !pack.isDownloading
    iconSource: Theme.subjectIcon(pack.subject)
}
