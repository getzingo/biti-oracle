# RPi kleines Projekt

## Infos

### Environment

- JoyPi mit Raspberry Pi 4B
- RPi OS trixie
- Python 3.13.5
- DHT11 Sensor auf Pin7 (GPIO4)
- HC-SR04 Ultraschall Distanzsensor: Trigger auf Pin32

### Auswahlkriterien

Für das "große Projekt" müssen ein paar Sensoren betrieben werden, deswegen habe ich diese in Kombination mit Pygame getestet.

Es ist eine ganz simple GUI mit zwei States, die bei Interaktion wechseln. Der Splashcreen ist `idle` und beinhaltet ein *schwebendes* Textelement.
State `measuring` liest die Sensoren aus und rendert die Daten dann auf den Screen.

In der gleichen Form soll das dann im großen Projekt passieren, nur mit mehr Spielereien.

### Ziele/Nicht Ziele

Das Ziel wurde unter anderem schon unter [Auswahlkriterien](#auswahlkriterien) beschrieben. Zusätzlich kommt aber noch dazu, dass ich keine Desktop Environment installieren möchte, um Ressourcen für die später eingesetzte LLM zu belegen, Zugriff passiert hauptsächlich ohnehin nur über SSH.
Nicht Ziele orientieren sich an den Zielen, es ist ein simples Setup, das nur die Interaktion zwischen Pygame und Sensoren darstellen soll.

### Hürden & RTFM

Ursprünglich sollte der Seeed Grove IR Temperatursensor die Messungen übernehmen, das erlag aber leider dem Problem, dass der RPi keine Analog-In Pins besitzt. Und ohne ADC musste der DHT11 als Temperatursensor verwendet werden.

Am schwierigsten war das Rendern von Pygame Inhalten auf den Screen ohne GUI. Claude Opus konnte das Problem nicht lösen, früher (unter Buster) konnte man einfach den richtigen Display mit `export DISPLAY=:0.0` setzen und dann konnte man auf diesen Display Inhalte rendern.

Das ging allerdings bei dem Versuch nicht so straight-forward.

Die erste Fehlerquelle war, dass ich das Package `pygame` mit pip in einer Virtuellen Environment installiert habe. [Das soll man aber nicht machen, sondern das OS-Package installieren.](https://www.pygame.org/wiki/GettingStarted#Unix%20Binary%20Packages)


`python3-pygame` und pip package `pygame` haben dieselbe Version schlussendlich:
```shell
apt policy python3-pygame
# python3-pygame:
#   Installed: 2.6.1-1+b2
#   Candidate: 2.6.1-1+b2
#   Version table:
#  *** 2.6.1-1+b2 500
#         500 http://deb.debian.org/debian trixie/main arm64 Packages
#         100 /var/lib/dpkg/status

pip3 index versions pygame
# pygame (2.6.1)
# Available versions: 2.6.1, 2.6.0, 2.5.2, 2.5.1, 2.5.0, 2.4.0, 2.3.0, 2.2.0, 2.1.3, 2.1.2, 2.1.1, 2.1.0, 2.0.3, 2.0.2, 2.0.1, 2.0.0, 1.9.6, 1.9.5, 1.9.4, 1.9.3, 1.9.2
#   INSTALLED: 2.6.1
#   LATEST:    2.6.1
```

Leider hat das pip package keine richtige Implementierung um den Kernel Mode-Setting Direct Rendering Manager (KMSDRM) mit dem Wayland Video Treiber zu verwenden, pygame wollte immer auf X11 zurückgreifen ([Quelle](https://forums.raspberrypi.com/viewtopic.php?t=367519 )). Deswegen über den OS Package Manager mit den Dependencies für das SDL Backend.

```shell
pip3 uninstall pygame
apt install python3-pygame libegl1 libegl-mesa0 libgles2

# Deswegen in venv/bin/activate richtigen Treiber einfügen
echo 'export SDL_VIDEODRIVER=kmsdrm' >> venv/bin/activate
```

Weiters muss man die Virtuelle Umgebung dann mit OS Package Referenz kreieren: 
```shell
python3 -m venv venv --system-site-packages
```

Es kann sein, dass man sich das alles mit der default Desktop Umgebung ersparen würde, es hat mich aber eh nur 3 Stunden gekostet.

## Installation

Voraussetzung ist ein funktionierender RPi, gearbeitet wurde unter dem OS `Raspberry Pi OS Lite`, der auf Debian 13 (trixie) basiert.

```shell
sudo apt-get update
sudo apt-get install -y \
  python3-dev \
  python3-pygame \
  python3-dotenv \
  gcc \
  libgpiod-dev \
  swig \
  liblgpio-dev \
  libegl1 \
  libegl-mesa0 \
  libgles2 \
  libgbm1 \
  libdrm2 \
  git
```

Der aktuelle User **muss** in den Gruppen `video, render, input, gpio, i2c, spi` sein:

```shell
USER=$(whoami)
sudo usermod -aG video,render,input,gpio,i2c,spi $USER
```

Dann dieses Repo klonen und den Projektordner wechseln. Anschliessend virtuelle Umgebung initialisieren und Pip Abhängigkeiten installieren:

```shell
git clone https://github.com/getzingo/biti-oracle
cd biti-oracle/kleines_projekt

# Venv initialisieren
python3 -m venv venv --system-site-packages
# DSM workaround
echo 'export SDL_VIDEODRIVER=kmsdrm' >> venv/bin/activate
source venv/bin/activate
```

Dann sollte in der Shell immer `venv` voranstehen, um zu signalisieren, dass die virtuelle Umgebung aktiv ist. Die meisten Betriebssysteme lassen es nämlich nicht zu, direkt Pip-Packages zu installieren. Für Python Module, die global verwendet werden müssen, sollte man immer den OS Packagemanager verwenden, wie etwa `apt install python3-dotenv`.

Um alle Python Module zu installieren, das bereitgestellte File `requirements.txt` verwenden:

```shell
pip3 install -r requirements.txt

# Zur Sicherheit nochmal pygame deinstallieren
pip3 uninstall pygame
```

### Demo ausführen

Es gibt auch ein Shell-Script um nicht diesen ganzen Prozess durchführen zu müssen:

```shell
./run-demo.sh

# Oder mit aktiver venv
python kleines_projekt_demo.py
```

