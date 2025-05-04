#include "beringerverwaltung.h"

#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    beringerverwaltung w;
    w.show();
    return a.exec();
}
