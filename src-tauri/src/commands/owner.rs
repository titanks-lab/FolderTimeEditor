use super::to_wide;
use std::ffi::c_void;
use std::ptr;

type HLOCAL = *mut c_void;

// Security constants
const SE_FILE_OBJECT: u32 = 1;
const OWNER_SECURITY_INFORMATION: u32 = 0x00000001;

// FFI 声明 Win32 API
extern "system" {
    fn GetNamedSecurityInfoW(
        pObjectName: *const u16,
        ObjectType: u32,
        SecurityInfo: u32,
        ppsidOwner: *mut *mut c_void,
        ppsidGroup: *mut *mut c_void,
        ppDacl: *mut *mut c_void,
        ppSacl: *mut *mut c_void,
        ppSecurityDescriptor: *mut *mut c_void,
    ) -> u32;

    fn SetNamedSecurityInfoW(
        pObjectName: *const u16,
        ObjectType: u32,
        SecurityInfo: u32,
        ppsidOwner: *mut c_void,
        ppsidGroup: *mut c_void,
        ppDacl: *mut c_void,
        ppSacl: *mut c_void,
    ) -> u32;

    fn ConvertSidToStringSidW(
        Sid: *mut c_void,
        StringSid: *mut *mut u16,
    ) -> i32;

    fn ConvertStringSidToSidW(
        StringSid: *const u16,
        Sid: *mut *mut c_void,
    ) -> i32;

    fn LocalFree(hMem: HLOCAL) -> HLOCAL;
}

/// 获取文件/目录的所有者（SID 字符串形式，如 "S-1-5-21-..."）
#[tauri::command]
pub fn get_file_owner(path: String) -> Result<String, String> {
    let wide = to_wide(&path);

    let mut psid_owner: *mut c_void = ptr::null_mut();
    let mut p_sd: *mut c_void = ptr::null_mut();

    // 获取安全描述符中的所有者 SID
    let result = unsafe {
        GetNamedSecurityInfoW(
            wide.as_ptr(),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION,
            &mut psid_owner,
            ptr::null_mut(),
            ptr::null_mut(),
            ptr::null_mut(),
            &mut p_sd,
        )
    };

    if result != 0 {
        if !p_sd.is_null() {
            let _ = unsafe { LocalFree(p_sd as HLOCAL) };
        }
        return Err(format!("无法获取所有者信息: {}", path));
    }

    // 将 SID 转换为字符串表示
    let mut pstr_sid: *mut u16 = ptr::null_mut();

    let success = unsafe {
        ConvertSidToStringSidW(psid_owner, &mut pstr_sid)
    };

    // 释放安全描述符
    let _ = unsafe { LocalFree(p_sd as HLOCAL) };

    if success == 0 || pstr_sid.is_null() {
        return Err("SID 转换为字符串失败".into());
    }

    let owner = unsafe {
        let len = (0..).take_while(|&i| *pstr_sid.offset(i) != 0).count();
        let slice = std::slice::from_raw_parts(pstr_sid, len);
        String::from_utf16_lossy(slice)
    };

    // 释放转换后的 SID 字符串
    let _ = unsafe { LocalFree(pstr_sid as HLOCAL) };

    Ok(owner)
}

/// 设置文件/目录的所有者
///
/// owner 参数接受 SID 字符串，如 "S-1-5-21-..." 或用户名 "Administrator"
#[tauri::command]
pub fn set_file_owner(path: String, owner: String) -> Result<(), String> {
    if owner.is_empty() {
        return Err("所有者不能为空".into());
    }

    let path_wide = to_wide(&path);
    let owner_wide = to_wide(&owner);

    // 将所有者字符串解析为 SID
    let mut psid: *mut c_void = ptr::null_mut();
    let success = unsafe {
        ConvertStringSidToSidW(owner_wide.as_ptr(), &mut psid)
    };

    if success == 0 || psid.is_null() {
        return Err(format!("无法解析所有者 SID: {}", owner));
    }

    // 设置所有者
    let result = unsafe {
        SetNamedSecurityInfoW(
            path_wide.as_ptr(),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION,
            psid,
            ptr::null_mut(),
            ptr::null_mut(),
            ptr::null_mut(),
        )
    };

    // 释放分配给 psid 的内存
    let _ = unsafe { LocalFree(psid as HLOCAL) };

    if result != 0 {
        return Err(format!("设置所有者失败: {}", path));
    }

    Ok(())
}
