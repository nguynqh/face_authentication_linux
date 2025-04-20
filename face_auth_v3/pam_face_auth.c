#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <sys/wait.h>

/* Function to get username from PAM */
static int get_username(pam_handle_t *pamh, const char **username) {
    int retval;
    retval = pam_get_user(pamh, username, NULL);
    if (retval != PAM_SUCCESS) {
        return retval;
    }
    if (*username == NULL || **username == '\0') {
        return PAM_USER_UNKNOWN;
    }
    return PAM_SUCCESS;
}

/* Run facial recognition script */
static int run_face_auth(const char *username) {
    pid_t child_pid;
    int status;
    
    child_pid = fork();
    
    if (child_pid == 0) {
        /* Child process */
        char *args[] = {
            "/usr/bin/python3",
            "/usr/lib/face-auth/face_auth_cli.py",
            (char*)username,
            NULL
        };
        
        /* Set display for X access if needed */
        char display_env[32] = "DISPLAY=:0";
        putenv(display_env);
        
        /* Execute the Python script */
        execv("/usr/bin/python3", args);
        
        /* If execv returns, there was an error */
        fprintf(stderr, "execv failed\n");
        exit(1);
    } else if (child_pid > 0) {
        /* Parent process */
        if (waitpid(child_pid, &status, 0) == -1) {
            return PAM_SYSTEM_ERR;
        }
        
        if (WIFEXITED(status)) {
            /* Check exit status of the child process */
            if (WEXITSTATUS(status) == 0) {
                return PAM_SUCCESS;
            } else {
                return PAM_AUTH_ERR;
            }
        }
        
        return PAM_SYSTEM_ERR;
    } else {
        /* Fork failed */
        return PAM_SYSTEM_ERR;
    }
}

/* PAM entry point for authentication */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username = NULL;
    int retval;
    
    /* Get the username */
    retval = get_username(pamh, &username);
    if (retval != PAM_SUCCESS) {
        return retval;
    }
    
    /* Check if face auth is registered for this user */
    char path[256];
    snprintf(path, sizeof(path), "/var/lib/face-auth/encodings/%s.json", username);
    if (access(path, F_OK) != 0) {
        /* Face auth not registered for this user, skip and let other modules handle it */
        return PAM_IGNORE;
    }
    
    /* Run facial recognition */
    retval = run_face_auth(username);
    
    return retval;
}

/* Required PAM module functions */
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}
