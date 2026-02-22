"""
BBS Test Items Definition

Central definition of all 14 Berg Balance Scale test items.
"""

BBS_TESTS = {
    1: {
        'name': 'Sitting to Standing',
        'name_ko': '앉아서 일어서기',
        'description': '의자에서 팔을 사용하지 않고 일어서기',
        'duration_seconds': None,
        'max_score': 4
    },
    2: {
        'name': 'Standing Unsupported',
        'name_ko': '지지없이 서기',
        'description': '2분간 지지없이 서있기',
        'duration_seconds': 120,
        'max_score': 4
    },
    3: {
        'name': 'Sitting Unsupported',
        'name_ko': '지지없이 앉기',
        'description': '2분간 등을 대지 않고 앉기',
        'duration_seconds': 120,
        'max_score': 4
    },
    4: {
        'name': 'Standing to Sitting',
        'name_ko': '서서 앉기',
        'description': '서있는 상태에서 앉기',
        'duration_seconds': None,
        'max_score': 4
    },
    5: {
        'name': 'Transfers',
        'name_ko': '이동하기',
        'description': '의자에서 의자로 이동',
        'duration_seconds': None,
        'max_score': 4
    },
    6: {
        'name': 'Standing Eyes Closed',
        'name_ko': '눈감고 서기',
        'description': '10초간 눈감고 서있기',
        'duration_seconds': 10,
        'max_score': 4
    },
    7: {
        'name': 'Standing Feet Together',
        'name_ko': '두발 모으고 서기',
        'description': '1분간 두발 모으고 서있기',
        'duration_seconds': 60,
        'max_score': 4
    },
    8: {
        'name': 'Reaching Forward',
        'name_ko': '팔 뻗기',
        'description': '팔을 앞으로 뻗기',
        'duration_seconds': None,
        'max_score': 4
    },
    9: {
        'name': 'Retrieving Object',
        'name_ko': '바닥 물건 집기',
        'description': '바닥에서 물건 집기',
        'duration_seconds': None,
        'max_score': 4
    },
    10: {
        'name': 'Turning Look Behind',
        'name_ko': '뒤돌아보기',
        'description': '좌우로 뒤돌아보기',
        'duration_seconds': None,
        'max_score': 4
    },
    11: {
        'name': 'Turning 360',
        'name_ko': '360도 회전',
        'description': '360도 회전하기',
        'duration_seconds': 4,
        'max_score': 4
    },
    12: {
        'name': 'Alternate Foot on Stool',
        'name_ko': '발판 발 교대',
        'description': '발판에 발 교대로 올리기 (8회)',
        'duration_seconds': 20,
        'max_score': 4
    },
    13: {
        'name': 'One Foot in Front',
        'name_ko': '일렬로 서기',
        'description': '30초간 일렬로 서기',
        'duration_seconds': 30,
        'max_score': 4
    },
    14: {
        'name': 'Standing One Foot',
        'name_ko': '한발 서기',
        'description': '한발로 10초간 서기',
        'duration_seconds': 10,
        'max_score': 4
    }
}


def get_test_by_id(test_id: int) -> dict:
    """Get test info by ID."""
    return BBS_TESTS.get(test_id, {})


def get_all_tests() -> list:
    """Get all tests as a sorted list."""
    return [
        {'id': test_id, **info}
        for test_id, info in sorted(BBS_TESTS.items())
    ]
