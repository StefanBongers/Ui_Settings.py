#include "dialogringserieneingabe.h"
#include "./ui_dialogringserieneingabe.h"

DialogRingserienEingabe::DialogRingserienEingabe(QWidget *parent)
    : QDialog(parent)
    , ui(new Ui::DialogRingserienEingabe)
{
    ui->setupUi(this);
}

DialogRingserienEingabe::~DialogRingserienEingabe()
{
    delete ui;
}

