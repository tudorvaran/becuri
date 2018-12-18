#!/usr/bin/env python3
"""
Script care genereaza secventa pentru luminat becuri.

Acest script genereaza un fisier care contine OPCODES prin intermediul carora
se modifica starea ledurilor pe instalatia de pe brad. Fisierul este transmis
catre brad prin intermediul interfetei web. Fisierul general o sa fie arhivat
pentru a ocupa mai putin spatiu.

Pe interfata web fiecare user poate urca maxim 3 secvente. Secventele sunt apoi
rulate in mod aleator. Exista si posibilitatea testarii unei secvente inainte 
de a fi urcata pe server. Testarea este limitata la 40 de secunde, iar
secventele principale sunt limitate la 180 de secunde.

README:
    Clasa NeoPixel returneaza un array de pixeli.
    Culorile sunt exprimate ca tuple RGB cu valori cuprinse intre 0 si 255.
    Functii disponibile:
    - fill((r, g, b))
        seteaza toti pixelii la culoarea RGB data
        functia fill face si commit
    - sleep(milliseconds)
        destul de descriptiv
    - commit()
        trimite starea actuala a pixelilor catre becuri
    - push()
        dupa incheierea secventei se apeleaza functia push pentru a scrie
    datele in fisierul out

Pixelii pot fi adresati si individual:
    pixels[2] = (r, g, b)
Aceasta modifica starea lor in array. Pentru a trimite modificarile catre bec
trebuie sa se faca commit.

Pentru debugging foloseste 'decoder.py'
"""

import neopixel
import random
import sys

PIXEL_NUM = 50

path = 'animation.txt'
if len(sys.argv) > 1:
    path = sys.argv[1]

pixels = neopixel.NeoPixel(PIXEL_NUM, path)


# Exemplu animatie
# Inlocuieste codul din try-except cu propiul tau algoritm
try:
    # Facem toate becurile Red = 30, Green = 12, Blue = 200
    # fill face si commit, asa ca nu e nevoie sa facem inca o data
    pixels.fill((30, 12, 200))
    # Dormim 500 ms ca sa ne bucuram de (30, 12, 200)
    pixels.sleep(500)
    # Schimbam culoarea primului pixel si facem commit pentru a activa modificarea
    pixels[0] = (127, 127, 127)
    pixels.commit()
    pixels.sleep(200)

except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pixels.commit()

# La final se face push pentru a se arhiva datele si a se scrie in fisierul out
pixels.push()