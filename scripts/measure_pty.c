#define _GNU_SOURCE
#include <pty.h>
#include <poll.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
static volatile sig_atomic_t child=0;
static void stop(int sig) { if(child>0) kill(-(pid_t)child,SIGKILL); _exit(128+sig); }
static long long ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (long long)t.tv_sec*1000000000LL+t.tv_nsec; }
static int send_all(int fd,char *b,ssize_t n) { while(n>0){ssize_t k=write(fd,b,n);if(k<0){if(errno==EINTR)continue;return -1;}b+=k;n-=k;}return 0; }
int main(int argc,char **argv) {
 if(argc<3)return 125;
 FILE *report=fopen(argv[1],"w");if(!report)return 125;
 signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGHUP,stop);
 int master;long long start=ns();pid_t pid=forkpty(&master,0,0,0);
 if(pid<0)return 125;
 if(pid==0){fclose(report);execvp(argv[2],argv+2);_exit(errno==ENOENT?127:126);}
 child=pid;fprintf(report,"{\"start_ns\":%lld,\"pid\":%d}\n",start,pid);fclose(report);
 struct pollfd fds[2]={{master,POLLIN,0},{STDIN_FILENO,POLLIN,0}};
 char buf[65536];
 for(;;){
  int n=poll(fds,2,-1);if(n<0){if(errno==EINTR)continue;break;}
  if(fds[0].revents&(POLLIN|POLLHUP|POLLERR)){
   ssize_t k=read(master,buf,sizeof(buf));if(k<=0)break;
   if(send_all(STDOUT_FILENO,buf,k)<0)break;
  }
  if(fds[1].revents&POLLIN){ssize_t k=read(STDIN_FILENO,buf,sizeof(buf));if(k<=0){kill(-pid,SIGKILL);break;}if(send_all(master,buf,k)<0)break;}
 }
 close(master);kill(-pid,SIGKILL);int status;while(waitpid(pid,&status,0)<0&&errno==EINTR){}
 return 0;
}
