CC=gcc
CFLAGS=-fPIC -Wall
LDFLAGS=-shared
TARGET=pam_face_auth.so
SOURCES=pam_face_auth.c
LIBS=-lpam

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LIBS)

install:
	cp $(TARGET) /lib/security/
	chmod 755 /lib/security/$(TARGET)

clean:
	rm -f $(TARGET)
