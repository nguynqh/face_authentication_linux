#!/usr/bin/env python3
import os
import sys
import cv2
import time
import json
import glob
import subprocess
from datetime import datetime

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, check=False, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=5)
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {
            'error': str(e)
        }

def get_system_info():
    """Get system information relevant to camera troubleshooting"""
    info = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'username': os.getenv('USER') or os.getenv('USERNAME') or run_command('whoami')['stdout'].strip(),
        'uid': os.getuid(),
        'euid': os.geteuid(),
        'groups': run_command('id')['stdout'].strip(),
        'kernel': run_command('uname -r')['stdout'].strip(),
        'distro': run_command('lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME')['stdout'].strip(),
        'display': os.getenv('DISPLAY'),
        'terminal': os.getenv('TERM'),
        'opencv_version': cv2.__version__,
        'python_version': sys.version
    }
    return info

def check_camera_devices():
    """Check available camera devices and their permissions"""
    devices = []
    
    # Check /dev/video* devices
    for device in sorted(glob.glob('/dev/video*')):
        try:
            stats = os.stat(device)
            devices.append({
                'path': device,
                'permissions': oct(stats.st_mode)[-3:],
                'user': run_command(f'stat -c "%U" {device}')['stdout'].strip(),
                'group': run_command(f'stat -c "%G" {device}')['stdout'].strip(),
                'readable': os.access(device, os.R_OK),
                'writable': os.access(device, os.W_OK),
                'device_major_minor': f"{os.major(stats.st_rdev)}:{os.minor(stats.st_rdev)}"
            })
        except Exception as e:
            devices.append({
                'path': device,
                'error': str(e)
            })
    
    # Get v4l2 device info if available
    v4l2_info = run_command('v4l2-ctl --list-devices')
    v4l2_controls = {}
    
    # Get detailed info for each camera
    for device in devices:
        if 'path' in device:
            v4l2_controls[device['path']] = run_command(f'v4l2-ctl --device={device["path"]} --all')
    
    return {
        'devices': devices,
        'v4l2_info': v4l2_info,
        'v4l2_controls': v4l2_controls,
        'driver_info': run_command('lsmod | grep video')
    }

def check_loaded_modules():
    """Check loaded kernel modules related to cameras"""
    modules = {
        'uvcvideo': run_command('lsmod | grep uvcvideo'),
        'videodev': run_command('lsmod | grep videodev'),
        'v4l2': run_command('lsmod | grep v4l2')
    }
    return modules

def check_camera_access_methods():
    """Try multiple methods to access the camera"""
    results = {}
    
    # Check all potential camera indices
    for idx in range(4):
        results[f'camera_{idx}'] = {}
        
        # Try standard access
        try:
            cap = cv2.VideoCapture(idx)
            is_opened = cap.isOpened()
            results[f'camera_{idx}']['standard'] = {
                'opened': is_opened
            }
            
            if is_opened:
                ret, frame = cap.read()
                results[f'camera_{idx}']['standard']['frame_read'] = ret
                results[f'camera_{idx}']['standard']['frame_shape'] = str(frame.shape) if ret and frame is not None else None
                
                # Try to get camera properties
                props = {}
                for prop_id in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, 
                               cv2.CAP_PROP_FPS, cv2.CAP_PROP_BRIGHTNESS]:
                    props[f'prop_{prop_id}'] = cap.get(prop_id)
                results[f'camera_{idx}']['standard']['properties'] = props
            
            cap.release()
        except Exception as e:
            results[f'camera_{idx}']['standard'] = {
                'error': str(e)
            }
        
        # Try with explicit V4L2 backend if available
        if hasattr(cv2, 'CAP_V4L2'):
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                is_opened = cap.isOpened()
                results[f'camera_{idx}']['v4l2'] = {
                    'opened': is_opened
                }
                
                if is_opened:
                    ret, frame = cap.read()
                    results[f'camera_{idx}']['v4l2']['frame_read'] = ret
                    results[f'camera_{idx}']['v4l2']['frame_shape'] = str(frame.shape) if ret and frame is not None else None
                
                cap.release()
            except Exception as e:
                results[f'camera_{idx}']['v4l2'] = {
                    'error': str(e)
                }
        
        # Try with direct device path
        device_path = f'/dev/video{idx}'
        if os.path.exists(device_path):
            try:
                cap = cv2.VideoCapture(device_path)
                is_opened = cap.isOpened()
                results[f'camera_{idx}']['direct_path'] = {
                    'opened': is_opened
                }
                
                if is_opened:
                    ret, frame = cap.read()
                    results[f'camera_{idx}']['direct_path']['frame_read'] = ret
                    results[f'camera_{idx}']['direct_path']['frame_shape'] = str(frame.shape) if ret and frame is not None else None
                
                cap.release()
            except Exception as e:
                results[f'camera_{idx}']['direct_path'] = {
                    'error': str(e)
                }
                
            # Try with v4l2 URL format
            try:
                cap = cv2.VideoCapture(f"v4l2:{device_path}")
                is_opened = cap.isOpened()
                results[f'camera_{idx}']['v4l2_url'] = {
                    'opened': is_opened
                }
                
                if is_opened:
                    ret, frame = cap.read()
                    results[f'camera_{idx}']['v4l2_url']['frame_read'] = ret
                
                cap.release()
            except Exception as e:
                results[f'camera_{idx}']['v4l2_url'] = {
                    'error': str(e)
                }
    
    return results

def check_opencv_backends():
    """Check which OpenCV backends are available"""
    backends = {}
    
    # Check common backends
    backend_flags = {
        'CAP_V4L': 'V4L',
        'CAP_V4L2': 'V4L2',
        'CAP_FFMPEG': 'FFMPEG',
        'CAP_GSTREAMER': 'GStreamer',
        'CAP_IMAGES': 'Images',
        'CAP_DSHOW': 'DirectShow'
    }
    
    for flag, name in backend_flags.items():
        if hasattr(cv2, flag):
            backends[name] = True
        else:
            backends[name] = False
    
    return backends

def main():
    """Main function to run all diagnostics"""
    results = {
        'system_info': get_system_info(),
        'camera_devices': check_camera_devices(),
        'loaded_modules': check_loaded_modules(),
        'opencv_backends': check_opencv_backends(),
        'camera_access': check_camera_access_methods()
    }
    
    # Save results to file
    output_file = '/tmp/camera_diagnostic_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Also save a text summary
    summary_file = '/tmp/camera_diagnostic_summary.txt'
    with open(summary_file, 'w') as f:
        f.write(f"Camera Diagnostic Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        # System info
        f.write("SYSTEM INFORMATION\n")
        f.write("-" * 40 + "\n")
        for key, value in results['system_info'].items():
            f.write(f"{key}: {value}\n")
        f.write("\n")
        
        # Camera devices
        f.write("CAMERA DEVICES\n")
        f.write("-" * 40 + "\n")
        for device in results['camera_devices'].get('devices', []):
            if 'error' in device:
                f.write(f"{device['path']}: ERROR - {device['error']}\n")
            else:
                f.write(f"{device['path']} - Permissions: {device['permissions']}, ")
                f.write(f"User: {device['user']}, Group: {device['group']}, ")
                f.write(f"Readable: {device['readable']}, Writable: {device['writable']}\n")
        f.write("\n")
        
        # OpenCV backends
        f.write("OPENCV BACKENDS\n")
        f.write("-" * 40 + "\n")
        for name, available in results['opencv_backends'].items():
            f.write(f"{name}: {'Available' if available else 'Not available'}\n")
        f.write("\n")
        
        # Camera access results
        f.write("CAMERA ACCESS TESTS\n")
        f.write("-" * 40 + "\n")
        for camera, methods in results['camera_access'].items():
            f.write(f"{camera}:\n")
            for method, result in methods.items():
                if 'error' in result:
                    f.write(f"  {method}: ERROR - {result['error']}\n")
                else:
                    f.write(f"  {method}: Opened: {result['opened']}")
                    if result.get('opened'):
                        f.write(f", Frame read: {result.get('frame_read', False)}")
                        if result.get('frame_shape'):
                            f.write(f", Frame shape: {result['frame_shape']}")
                    f.write("\n")
            f.write("\n")
        
    print(f"Camera diagnostics completed. Results saved to {output_file}")
    print(f"Summary saved to {summary_file}")
    
    # Print a short summary
    print("\nBrief Summary:")
    print("-" * 40)
    devices_found = len(results['camera_devices'].get('devices', []))
    print(f"Camera devices found: {devices_found}")
    
    success = False
    for camera, methods in results['camera_access'].items():
        for method, result in methods.items():
            if result.get('opened') and result.get('frame_read', False):
                print(f"✓ Successfully opened and read frames from {camera} using {method}")
                success = True
    
    if not success:
        print("✗ Failed to successfully open any camera and read frames")
    
    # Print potential issues and solutions
    print("\nDiagnostic:")
    if not devices_found:
        print("❌ No camera devices found in /dev/video*")
        print("   Possible solutions:")
        print("   - Check if camera is properly connected")
        print("   - Reload uvcvideo kernel module: sudo modprobe -r uvcvideo && sudo modprobe uvcvideo")
    else:
        all_failed = True
        for camera, methods in results['camera_access'].items():
            for method, result in methods.items():
                if result.get('opened'):
                    all_failed = False
                    
        if all_failed:
            print("❌ Camera devices found but could not be opened")
            print("   Possible solutions:")
            print("   - Add user to video group: sudo usermod -a -G video $USER")
            print("   - Fix permissions: sudo chmod 666 /dev/video*")
            print("   - Check if another process is using the camera")
            print("   - Try rebooting the system")
    
    for idx, access_results in results['camera_access'].items():
        for method, result in access_results.items():
            if result.get('opened') and not result.get('frame_read', False):
                print(f"❌ {idx} opened with {method} but couldn't read frames")
                print("   Possible solution: Check for camera driver issues or hardware problems")

if __name__ == '__main__':
    main()