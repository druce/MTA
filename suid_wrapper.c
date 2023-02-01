#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
/* #include <sys/types.h>
*/

/* 
gcc -o suid_wrapper suid_wrapper.c
sudo chown root:root suid_wrapper
sudo chmod 6777 suid_wrapper 
sudo mv suid_wrapper suid_stop_plotlydash
*/

int main(void)
{
  setuid(0);
  system("supervisorctl stop plotlydash");
  system("pkill -f app.py");
}
