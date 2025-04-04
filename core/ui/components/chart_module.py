def _transform_daily_data_to_candles(self, data):
        """일봉 데이터를 캔들스틱 포맷으로 변환"""
        if not data or not isinstance(data, list):
            logger.warning("일봉 데이터 변환 오류: 유효하지 않은 데이터 형식")
            return []
        
        try:
            candles = []
            for item in data:
                if not item:
                    continue
                
                # 일봉 데이터 구조: 날짜, 시가, 고가, 저가, 종가, 거래량, ...
                date_str = item.get("stck_bsop_date", "")
                
                # 날짜 형식 변환 (20220101 -> timestamp로 변환)
                if date_str and len(date_str) == 8:
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    timestamp = int(date_obj.timestamp())
                else:
                    continue  # 유효하지 않은 날짜 건너뛰기
                
                # 가격 데이터 변환 (소수점 적용 처리)
                try:
                    # 소수점 위치 확인 (소수점 없으면 0)
                    decimal_point = 0
                    
                    # OHLC 추출 및 변환
                    open_val = float(item.get("stck_oprc", "0"))
                    high = float(item.get("stck_hgpr", "0"))
                    low = float(item.get("stck_lwpr", "0"))
                    close = float(item.get("stck_clpr", "0"))
                    volume = float(item.get("acml_vol", "0"))
                    
                    # 데이터 검증
                    if all(v > 0 for v in [open_val, high, low, close]):
                        # 시간, 시가, 고가, 저가, 종가, 거래량 순서로 저장
                        candle = [timestamp, open_val, high, low, close, volume]
                        candles.append(candle)
                except (ValueError, TypeError) as e:
                    logger.warning(f"일봉 데이터 변환 중 값 파싱 오류: {e}, 항목: {item}")
                    continue
            
            # 오래된 데이터가 먼저 오도록 정렬 (시간 오름차순)
            candles.sort(key=lambda x: x[0])
            logger.info(f"일봉 데이터 변환 완료: {len(candles)}개 캔들 생성")
            return candles
            
        except Exception as e:
            logger.error(f"일봉 데이터 변환 중 오류 발생: {e}", exc_info=True)
            return [] 