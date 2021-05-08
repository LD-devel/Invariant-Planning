(define (problem strips-sat-x-1)
(:domain satellite)
(:objects
	satellite0 - satellite
	instrument0 - instrument
	instrument1 - instrument
	instrument2 - instrument
	satellite1 - satellite
	instrument3 - instrument
	image1 - mode
	infrared0 - mode
	spectrograph2 - mode
	star1 - direction
	star2 - direction
	star0 - direction
	star3 - direction
	star4 - direction
	phenomenon5 - direction
	phenomenon6 - direction
	phenomenon7 - direction
)
(:init
	(supports instrument0 spectrograph2)
	(supports instrument0 infrared0)
	(calibration_target instrument0 star1)
	(supports instrument1 image1)
	(calibration_target instrument1 star2)
	(supports instrument2 infrared0)
	(supports instrument2 image1)
	(calibration_target instrument2 star0)
	(on_board instrument0 satellite0)
	(on_board instrument1 satellite0)
	(on_board instrument2 satellite0)
	(power_avail satellite0)
	(pointing satellite0 star4)
	(= (data_capacity satellite0) 1000)
	(= (fuel satellite0) 108)
	(supports instrument3 spectrograph2)
	(supports instrument3 infrared0)
	(supports instrument3 image1)
	(calibration_target instrument3 star0)
	(on_board instrument3 satellite1)
	(power_avail satellite1)
	(pointing satellite1 star0)
	(= (data_capacity satellite1) 1000)
	(= (fuel satellite1) 174)
	(= (data star3 image1) 208)
	(= (data star4 image1) 156)
	(= (data phenomenon5 image1) 205)
	(= (data phenomenon6 image1) 247)
	(= (data phenomenon7 image1) 122)
	(= (data star3 infrared0) 164)
	(= (data star4 infrared0) 196)
	(= (data phenomenon5 infrared0) 95)
	(= (data phenomenon6 infrared0) 67)
	(= (data phenomenon7 infrared0) 248)
	(= (data star3 spectrograph2) 125)
	(= (data star4 spectrograph2) 6)
	(= (data phenomenon5 spectrograph2) 44)
	(= (data phenomenon6 spectrograph2) 222)
	(= (data phenomenon7 spectrograph2) 78)
	(= (slew_time star1 star0) 34.35)
	(= (slew_time star0 star1) 34.35)
	(= (slew_time star2 star0) 8.768)
	(= (slew_time star0 star2) 8.768)
	(= (slew_time star2 star1) 18.57)
	(= (slew_time star1 star2) 18.57)
	(= (slew_time star3 star0) 25.66)
	(= (slew_time star0 star3) 25.66)
	(= (slew_time star3 star1) 25.96)
	(= (slew_time star1 star3) 25.96)
	(= (slew_time star3 star2) 17.99)
	(= (slew_time star2 star3) 17.99)
	(= (slew_time star4 star0) 71.99)
	(= (slew_time star0 star4) 71.99)
	(= (slew_time star4 star1) 1.526)
	(= (slew_time star1 star4) 1.526)
	(= (slew_time star4 star2) 35.34)
	(= (slew_time star2 star4) 35.34)
	(= (slew_time star4 star3) 49.61)
	(= (slew_time star3 star4) 49.61)
	(= (slew_time phenomenon5 star0) 67.92)
	(= (slew_time star0 phenomenon5) 67.92)
	(= (slew_time phenomenon5 star1) 4.095)
	(= (slew_time star1 phenomenon5) 4.095)
	(= (slew_time phenomenon5 star2) 30.24)
	(= (slew_time star2 phenomenon5) 30.24)
	(= (slew_time phenomenon5 star3) 7.589)
	(= (slew_time star3 phenomenon5) 7.589)
	(= (slew_time phenomenon5 star4) 0.5297)
	(= (slew_time star4 phenomenon5) 0.5297)
	(= (slew_time phenomenon6 star0) 77.1)
	(= (slew_time star0 phenomenon6) 77.1)
	(= (slew_time phenomenon6 star1) 47.3)
	(= (slew_time star1 phenomenon6) 47.3)
	(= (slew_time phenomenon6 star2) 64.11)
	(= (slew_time star2 phenomenon6) 64.11)
	(= (slew_time phenomenon6 star3) 51.56)
	(= (slew_time star3 phenomenon6) 51.56)
	(= (slew_time phenomenon6 star4) 56.36)
	(= (slew_time star4 phenomenon6) 56.36)
	(= (slew_time phenomenon6 phenomenon5) 67.57)
	(= (slew_time phenomenon5 phenomenon6) 67.57)
	(= (slew_time phenomenon7 star0) 9.943)
	(= (slew_time star0 phenomenon7) 9.943)
	(= (slew_time phenomenon7 star1) 13.3)
	(= (slew_time star1 phenomenon7) 13.3)
	(= (slew_time phenomenon7 star2) 60.53)
	(= (slew_time star2 phenomenon7) 60.53)
	(= (slew_time phenomenon7 star3) 53.93)
	(= (slew_time star3 phenomenon7) 53.93)
	(= (slew_time phenomenon7 star4) 67.87)
	(= (slew_time star4 phenomenon7) 67.87)
	(= (slew_time phenomenon7 phenomenon5) 43.97)
	(= (slew_time phenomenon5 phenomenon7) 43.97)
	(= (slew_time phenomenon7 phenomenon6) 32.34)
	(= (slew_time phenomenon6 phenomenon7) 32.34)
	(= (data-stored) 0)
	(= (fuel-used) 0)
)
(:goal (and
	(pointing satellite0 phenomenon5)
	(have_image star3 infrared0)
	(have_image star4 spectrograph2)
	(have_image phenomenon5 spectrograph2)
	(have_image phenomenon7 spectrograph2)
))
)