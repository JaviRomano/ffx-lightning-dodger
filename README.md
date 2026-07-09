# FFX Lightning Dodger

Herramienta de automatizacion de videojuegos basada en vision por computador, escrita en Python.

## Descripcion

Automatizacion en tiempo real que detecta un patron visual en pantalla y ejecuta una respuesta de input de forma automatica. El sistema usa una arquitectura multi-hilo: un hilo se encarga de la captura de pantalla, otro de la deteccion del patron y otro de la simulacion de input, ejecutandose de forma concurrente para minimizar la latencia.

## Stack

Python, OpenCV, mss (captura de pantalla), pynput (simulacion de input).

## Caracteristicas

Arquitectura multi-hilo con captura de pantalla, deteccion de patrones y simulacion de input ejecutandose de forma concurrente.<br>
Calibracion manual de la region de interes (ROI), del umbral HSV y del nivel de confianza, para ajustar la deteccion a las condiciones reales del juego.<br>
Latencia de respuesta de aproximadamente 215 ms.

## Contexto

Este proyecto nace de un ejercicio de ingenieria inversa practica: entender el comportamiento visual de un sistema externo y construir sobre el una solucion de automatizacion fiable.

## Nota

Proyecto con fines educativos y de demostracion tecnica de vision por computador en tiempo real.
