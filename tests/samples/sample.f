       PROGRAM sample
       
       LOGICAL BLAH
       
       IF (BLAH) A=1.0
       IF (BLAH) THEN
           B=1.0
       ELSEIF (A > 1.0) THEN
           B=2.0
       ELSE
           C=1.0
       ENDIF
       
       DO 10, I=1,10
           print *,I
10     CONTINUE
       
       DO I=1,20
           print *,I
       ENDDO
       
       RETURN
