#ifndef DIALOGRINGSERIENEINGABE_H
#define DIALOGRINGSERIENEINGABE_H

#include <QDialog>

QT_BEGIN_NAMESPACE
namespace Ui { class DialogRingserienEingabe; }
QT_END_NAMESPACE

class DialogRingserienEingabe : public QDialog
{
    Q_OBJECT

public:
    DialogRingserienEingabe(QWidget *parent = nullptr);
    ~DialogRingserienEingabe();

private:
    Ui::DialogRingserienEingabe *ui;
};
#endif // DIALOGRINGSERIENEINGABE_H
