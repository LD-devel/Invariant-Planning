;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_32)
  (:domain fn-counters-inv)
  (:objects
    c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 - counter
  )

  (:init
    (= (max_int) 64)
	(= (value c0) 62)
	(= (value c1) 60)
	(= (value c2) 58)
	(= (value c3) 56)
	(= (value c4) 54)
	(= (value c5) 52)
	(= (value c6) 50)
	(= (value c7) 48)
	(= (value c8) 46)
	(= (value c9) 44)
	(= (value c10) 42)
	(= (value c11) 40)
	(= (value c12) 38)
	(= (value c13) 36)
	(= (value c14) 34)
	(= (value c15) 32)
	(= (value c16) 30)
	(= (value c17) 28)
	(= (value c18) 26)
	(= (value c19) 24)
	(= (value c20) 22)
	(= (value c21) 20)
	(= (value c22) 18)
	(= (value c23) 16)
	(= (value c24) 14)
	(= (value c25) 12)
	(= (value c26) 10)
	(= (value c27) 8)
	(= (value c28) 6)
	(= (value c29) 4)
	(= (value c30) 2)
	(= (value c31) 0)
  )

  (:goal (and 
(<= (+ (value c0) 1) (value c1))
(<= (+ (value c1) 1) (value c2))
(<= (+ (value c2) 1) (value c3))
(<= (+ (value c3) 1) (value c4))
(<= (+ (value c4) 1) (value c5))
(<= (+ (value c5) 1) (value c6))
(<= (+ (value c6) 1) (value c7))
(<= (+ (value c7) 1) (value c8))
(<= (+ (value c8) 1) (value c9))
(<= (+ (value c9) 1) (value c10))
(<= (+ (value c10) 1) (value c11))
(<= (+ (value c11) 1) (value c12))
(<= (+ (value c12) 1) (value c13))
(<= (+ (value c13) 1) (value c14))
(<= (+ (value c14) 1) (value c15))
(<= (+ (value c15) 1) (value c16))
(<= (+ (value c16) 1) (value c17))
(<= (+ (value c17) 1) (value c18))
(<= (+ (value c18) 1) (value c19))
(<= (+ (value c19) 1) (value c20))
(<= (+ (value c20) 1) (value c21))
(<= (+ (value c21) 1) (value c22))
(<= (+ (value c22) 1) (value c23))
(<= (+ (value c23) 1) (value c24))
(<= (+ (value c24) 1) (value c25))
(<= (+ (value c25) 1) (value c26))
(<= (+ (value c26) 1) (value c27))
(<= (+ (value c27) 1) (value c28))
(<= (+ (value c28) 1) (value c29))
(<= (+ (value c29) 1) (value c30))
(<= (+ (value c30) 1) (value c31))
  ))

  
)
