from __future__ import annotations

import pytest

ITEM = {
    "id": "9c5xxxxxxxxxx",
    "type": "file",
    "links": {"self": "https://www.virustotal.com/api/v3/files/9c5xxxxxxxxxx"},
    "attributes": {
        "trid": [{"file_type": "Android Package", "probability": 49}],
        "sha256": "9c5xxxxxxxxxx",
        "times_submitted": 59750,
        "type_extension": "apk",
        "reputation": 0,
        "sha1": "f7dxxxxxxxxxx",
        "meaningful_name": "Ludio_Player.apk",
        "last_analysis_date": 1740481863,
        "magika": "APK",
        "names": ["Ludio_Player.apk", "base.apk"],
        "type_tag": "android",
        "ssdeep": "19xxxx:mx3xxxxxxxxxx",
        "type_tags": ["executable", "mobile"],
        "vhash": "577xxxxxxxxxx",
        "last_analysis_results": {
            "Bkav": {
                "method": "blacklist",
                "engine_name": "Bkav",
                "engine_version": "2.0.0.1",
                "engine_update": "202xxxxx",
                "category": "undetected",
                "result": "",
            },
            "Lionic": {
                "method": "blacklist",
                "engine_name": "Lionic",
                "engine_version": "8.16",
                "engine_update": "202xxxxx",
                "category": "undetected",
                "result": "",
            },
        },
        "exiftool": {
            "ZipRequiredVersion": "20",
            "MIMEType": "application/zip",
            "ZipCRC": "0xaxxxxxxx",
            "FileType": "ZIP",
            "ZipCompression": "Deflated",
            "ZipUncompressedSize": "14208",
            "ZipCompressedSize": "3434",
            "FileTypeExtension": "zip",
            "ZipFileName": "AndroidManifest.xml",
            "ZipBitFlag": "0x0808",
            "ZipModifyDate": "2016:01:10 17:03:08",
        },
        "permhash": "a0bxxxxxxxxxx",
        "threat_severity": {
            "version": 5,
            "threat_severity_level": "SEVERITY_NONE",
            "threat_severity_data": {"num_av_detections": 2},
            "last_analysis_date": "1728081112",
            "level_description": "Severity NONE because the file"
                                 " has no Google antivirus detections "
                                 "and no bad network activity",
        },
        "bundle_info": {
            "highest_datetime": "2016-01-10 17:03:08",
            "lowest_datetime": "2016-01-10 17:03:08",
            "num_children": 2100,
            "extensions": {"xml": 232, "dex": 1},
            "file_types": {"XML": 232, "DEX": 1},
            "type": "APK",
            "uncompressed_size": 28102995,
        },
        "tlsh": "T1Cxxxxxxxxxx",
        "downloadable": "true",
        "md5": "544xxxxxxxxxx",
        "type_description": "Android",
        "unique_sources": 76,
        "last_modification_date": 1740482034,
        "filecondis": {"dhash": "000xxxxxxxxxx", "raw_md5": "e45xxxxxxxxxx"},
        "size": 14267767,
        "total_votes": {"harmless": 0, "malicious": 0},
        "first_submission_date": 1615438126,
        "available_tools": [],
        "main_icon": {"raw_md5": "470xxxxxxxxxx", "dhash": "c4dxxxxxxxxxx"},
        "last_analysis_stats": {
            "malicious": 2,
            "suspicious": 0,
            "undetected": 66,
            "harmless": 0,
            "timeout": 1,
            "confirmed-timeout": 0,
            "failure": 0,
            "type-unsupported": 8,
        },
        "magic": "Java archive data (JAR)",
        "androguard": {
            "VTAndroidInfo": 2,
            "AndroidApplicationError": "false",
            "MinSdkVersion": "21",
            "AndroguardVersion": "4.1.2",
            "Activities": [
                "com.mr.ludiop.activity.PlayerSplashActivity",
                "com.google.android.gms.common.api.GoogleApiActivity",
            ],
            "certificate": {
                "Subject": {"DN": "CN:editor", "CN": "editor"},
                "validto": "2115-12-17 08:03:09",
                "serialnumber": "231xxxxx",
                "thumbprint": "927xxxxxxxxxx",
                "validfrom": "2016-01-10 08:03:09",
                "Issuer": {"DN": "CN:editor", "CN": "editor"},
            },
            "AndroidApplication": 1,
            "RiskIndicator": {
                "APK": {"DEX": 1, "SHARED LIBRARIES": 20},
                "PERM": {
                    "DANGEROUS": 2,
                    "INTERNET": 1,
                    "INSTANT": 2,
                    "NORMAL": 4,
                },
            },
            "Services": [
                "com.google.android.gms.cast.framework.ReconnectionService",
                "com.google.android.gms.cast.framework.media.MediaNotificationService",
            ],
            "AndroidVersionCode": "130xxxxx",
            "Package": "com.mr.ludiop",
            "AndroidVersionName": "2.0.0",
            "TargetSdkVersion": "30",
            "AndroidApplicationInfo": "APK",
            "Providers": [
                "androidx.core.content.FileProvider",
                "androidx.lifecycle.ProcessLifecycleOwnerInitializer",
            ],
            "Receivers": [
                "com.google.android.gms.cast.framework.media.MediaIntentReceiver"
            ],
            "StringsInformation": ["http://cablegratishd.com/"],
            "main_activity": "com.mr.ludiop.activity.PlayerSplashActivity",
            "intent_filters": {
                "Activities": {
                    "com.mr.ludiop.iptvReader.MainIptvActivity": {
                        "action": ["android.intent.action.VIEW"]
                    }
                },
                "Receivers": {
                    "com.google.firebase.iid.FirebaseInstanceIdReceiver": {
                        "action": ["com.google.android.c2dm.intent.RECEIVE"]
                    }
                },
            },
            "permission_details": {
                "android.permission.READ_EXTERNAL_STORAGE": {
                    "permission_type": "dangerous"
                }
            },
        },
        "last_submission_date": 1740481863,
        "tags": ["runtime-modules", "mysql-communication"],
        "gti_assessment": {
            "verdict": {"value": "VERDICT_UNDETECTED"},
            "threat_score": {"value": 1},
            "severity": {"value": "SEVERITY_NONE"},
            "description": "This indicator did not match our "
                           "detection criteria and there is "
                           "currently no evidence of malicious activity.",
        },
    },
}

SUCCESS_RESPONSE = {"data": [ITEM]}


@pytest.fixture
def success_search_response():
    return SUCCESS_RESPONSE


@pytest.fixture
def get_item_response():
    return ITEM
