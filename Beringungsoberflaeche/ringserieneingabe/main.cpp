#include "dialogringserieneingabe.h"

#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    DialogRingserienEingabe w;
    w.show();
    return a.exec();
}
