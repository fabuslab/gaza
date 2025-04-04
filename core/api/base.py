"""
API 기본 모듈
"""

import logging
from typing import Dict, Optional
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class APIError(Exception):
    """API 오류"""
    pass

class BaseAPI:
    """API 기본 클래스"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Args:
            base_url: API 기본 URL
            api_key: API 키
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict[str, str]:
        """요청 헤더 생성"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """API 요청 전송
        
        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            params: URL 파라미터
            data: 요청 데이터
            **kwargs: 추가 파라미터
            
        Returns:
            응답 데이터
            
        Raises:
            APIError: API 요청 실패
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
            
        except RequestException as e:
            logger.error(f"API 요청 실패: {e}")
            raise APIError(f"API 요청 실패: {e}")
            
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        """GET 요청 전송"""
        return self._request("GET", endpoint, params=params, **kwargs)
        
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict:
        """POST 요청 전송"""
        return self._request("POST", endpoint, data=data, **kwargs)
        
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict:
        """PUT 요청 전송"""
        return self._request("PUT", endpoint, data=data, **kwargs)
        
    def delete(self, endpoint: str, **kwargs) -> Dict:
        """DELETE 요청 전송"""
        return self._request("DELETE", endpoint, **kwargs) 