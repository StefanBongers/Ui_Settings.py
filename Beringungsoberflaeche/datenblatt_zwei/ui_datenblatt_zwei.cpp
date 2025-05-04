#include "ui_datenblatt_zwei.h"
#include "./ui_ui_datenblatt_zwei.h"

Ui_Datenblatt_zwei::Ui_Datenblatt_zwei(QWidget *parent)
    : QDialog(parent)
    , ui(new Ui::Ui_Datenblatt_zwei)
{
    ui->setupUi(this);
}

Ui_Datenblatt_zwei::~Ui_Datenblatt_zwei()
{
    delete ui;
}

