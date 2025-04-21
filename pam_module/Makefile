CC = gcc
CFLAGS = -fPIC -Wall -I/usr/include
LDFLAGS = -shared
TARGET = pam_face_auth.so
SOURCES = pam_face_auth.c
OBJECTS = $(SOURCES:.c=.o)
LIBS = -lpam

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $^ $(LIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

install: $(TARGET)
	sudo install -m 755 $(TARGET) /usr/lib/x86_64-linux-gnu/security/

clean:
	rm -f $(OBJECTS) $(TARGET)
