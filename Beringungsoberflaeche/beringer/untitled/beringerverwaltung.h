#ifndef BERINGERVERWALTUNG_H
#define BERINGERVERWALTUNG_H

#include <QDialog>

QT_BEGIN_NAMESPACE
namespace Ui { class beringerverwaltung; }
QT_END_NAMESPACE

class beringerverwaltung : public QDialog
{
    Q_OBJECT

public:
    beringerverwaltung(QWidget *parent = nullptr);
    ~beringerverwaltung();

private:
    Ui::beringerverwaltung *ui;
};
#endif // BERINGERVERWALTUNG_H
