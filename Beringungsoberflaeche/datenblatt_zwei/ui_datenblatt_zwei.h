#ifndef UI_DATENBLATT_ZWEI_H
#define UI_DATENBLATT_ZWEI_H

#include <QDialog>

QT_BEGIN_NAMESPACE
namespace Ui { class Ui_Datenblatt_zwei; }
QT_END_NAMESPACE

class Ui_Datenblatt_zwei : public QDialog
{
    Q_OBJECT

public:
    Ui_Datenblatt_zwei(QWidget *parent = nullptr);
    ~Ui_Datenblatt_zwei();

private:
    Ui::Ui_Datenblatt_zwei *ui;
};
#endif // UI_DATENBLATT_ZWEI_H
