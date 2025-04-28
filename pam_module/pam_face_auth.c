#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <pwd.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <syslog.h>

#define FACE_AUTH_UI_PATH "/usr/bin/face_auth_ui"

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    int ret;
    const char *username = NULL;
    char *display_env;
    int use_face_auth = 1;  // Mặc định sử dụng xác thực khuôn mặt
    
    // Đọc các tham số
    for (int i = 0; i < argc; i++) {
        if (strncmp(argv[i], "disable=", 8) == 0) {
            if (strcmp(argv[i] + 8, "1") == 0) {
                use_face_auth = 0;
            }
        }
    }
    
    // Kiểm tra xem có bị vô hiệu hóa không
    if (!use_face_auth) {
        return PAM_IGNORE;
    }
    
    // Lấy tên người dùng
    ret = pam_get_user(pamh, &username, NULL);
    if (ret != PAM_SUCCESS) {
        syslog(LOG_ERR, "pam_face_auth: Failed to get username");
        return ret;
    }
    
    // Kiểm tra DISPLAY để đảm bảo chúng ta có giao diện đồ họa
    display_env = getenv("DISPLAY");
    if (!display_env || strlen(display_env) == 0) {
        syslog(LOG_NOTICE, "pam_face_auth: No display available, skipping face authentication");
        return PAM_IGNORE;
    }
    
    // Kiểm tra xem người dùng đã đăng ký xác thực khuôn mặt chưa
    char face_id_path[256];
    snprintf(face_id_path, sizeof(face_id_path), "/var/lib/face-auth/%s.txt", username);
    if (access(face_id_path, F_OK) != 0) {
        syslog(LOG_NOTICE, "pam_face_auth: User %s has no face ID registered", username);
        return PAM_IGNORE;
    }
    
    syslog(LOG_NOTICE, "pam_face_auth: Starting face authentication for user %s", username);
    
    // Fork process để hiển thị giao diện xác thực
    pid_t pid = fork();
    if (pid == -1) {
        syslog(LOG_ERR, "pam_face_auth: Fork failed");
        return PAM_SYSTEM_ERR;
    }
    
    if (pid == 0) {
        // Process con: chạy ứng dụng xác thực
        // Lấy XAUTHORITY từ user
        struct passwd *pw = getpwnam(username);
        if (pw) {
            char xauth_path[256];
            snprintf(xauth_path, sizeof(xauth_path), "%s/.Xauthority", pw->pw_dir);
            setenv("XAUTHORITY", xauth_path, 1);
        }
        
        // Đảm bảo chạy với quyền của user, không phải root
        if (setgid(pw->pw_gid) != 0 || setuid(pw->pw_uid) != 0) {
            syslog(LOG_ERR, "pam_face_auth: Failed to drop privileges");
            exit(1);
        }
        
        // Chạy ứng dụng giao diện xác thực
        execl(FACE_AUTH_UI_PATH, FACE_AUTH_UI_PATH, username, NULL);
        
        // Nếu execl thất bại
        syslog(LOG_ERR, "pam_face_auth: Failed to execute face authentication UI");
        exit(1);
    } else {
        // Process cha: đợi kết quả
        int status;
        waitpid(pid, &status, 0);
        
        if (WIFEXITED(status)) {
            int exit_code = WEXITSTATUS(status);
            if (exit_code == 0) {
                syslog(LOG_NOTICE, "pam_face_auth: Face authentication successful for user %s", username);
                return PAM_SUCCESS;
            } else {
                syslog(LOG_NOTICE, "pam_face_auth: Face authentication failed for user %s", username);
                return PAM_AUTH_ERR;
            }
        } else {
            syslog(LOG_ERR, "pam_face_auth: Authentication process terminated abnormally");
            return PAM_AUTH_ERR;
        }
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
