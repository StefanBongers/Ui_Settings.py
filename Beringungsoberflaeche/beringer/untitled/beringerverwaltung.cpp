#include "beringerverwaltung.h"
#include "./ui_beringerverwaltung.h"

beringerverwaltung::beringerverwaltung(QWidget *parent)
    : QDialog(parent)
    , ui(new Ui::beringerverwaltung)
{
    ui->setupUi(this);
}

beringerverwaltung::~beringerverwaltung()
{
    delete ui;
}

