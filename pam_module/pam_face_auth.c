#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <syslog.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>

//#define FACE_AUTH_SCRIPT "/usr/local/bin/face_auth.py"
#define FACE_AUTH_SCRIPT "/home/nguynqh/face_auth_system/start_face_auth.sh"

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *user;
    int ret;
    
    // Lấy tên người dùng hiện tại
    ret = pam_get_user(pamh, &user, NULL);
    if (ret != PAM_SUCCESS) {
        return ret;
    }
    
    // Thực hiện kiểm tra xác thực khuôn mặt bằng cách gọi script Python
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --username %s 2>/dev/null", FACE_AUTH_SCRIPT, user);
    
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        pam_syslog(pamh, LOG_ERR, "Cannot run face authentication script");
        return PAM_AUTH_ERR;
    }
    
    char result[16];
    if (fgets(result, sizeof(result), fp) == NULL) {
        pclose(fp);
        pam_syslog(pamh, LOG_ERR, "Error reading result from face authentication script");
        return PAM_AUTH_ERR;
    }
    
    pclose(fp);
    
    // Kiểm tra kết quả xác thực
    if (strncmp(result, "SUCCESS", 7) == 0) {
        return PAM_SUCCESS;
    } else {
        return PAM_AUTH_ERR;
    }
}

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
